"""
End-to-end checks against a running stack (docker compose up).

    E2E_PASSWORD=... python scripts/e2e.py           # run all checks, exit 1 on failure
    python scripts/e2e.py counts                     # print row counts (for restart checks)

Env: E2E_BASE_URL (default http://localhost:8000), E2E_USER (default admin), E2E_PASSWORD.
Stdlib only, so it runs anywhere without installing the app's requirements.
"""
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get('E2E_BASE_URL', 'http://localhost:8000')
USER = os.environ.get('E2E_USER', 'admin')
PASSWORD = os.environ.get('E2E_PASSWORD', '')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Browser:
    """Minimal cookie-keeping client. Sends cookies regardless of the Secure flag (as browsers do on localhost)."""

    def __init__(self, headers=None):
        self.cookies = {}
        self.headers = headers or {}
        self.opener = urllib.request.build_opener(NoRedirect)

    def request(self, method, path, data=None, headers=None):
        h = {**self.headers, **(headers or {})}
        if self.cookies:
            h['Cookie'] = '; '.join(f'{k}={v}' for k, v in self.cookies.items())
        body = urllib.parse.urlencode(data).encode() if isinstance(data, dict) else data
        try:
            resp = self.opener.open(urllib.request.Request(BASE + path, data=body, method=method, headers=h))
        except urllib.error.HTTPError as e:
            resp = e
        for cookie in resp.headers.get_all('Set-Cookie') or []:
            key, value = cookie.split(';')[0].split('=', 1)
            self.cookies[key] = value
        return resp.status, resp.headers, resp.read()

    def login(self, origin=BASE):
        _, _, body = self.request('GET', '/api/auth/login/')
        token = re.search(rb'name="csrfmiddlewaretoken" value="([^"]+)"', body).group(1).decode()
        return self.request('POST', '/api/auth/login/',
                            {'username': USER, 'password': PASSWORD, 'csrfmiddlewaretoken': token, 'next': '/'},
                            {'Origin': origin, 'Referer': origin + '/api/auth/login/'})


def count(path):
    return json.load(urllib.request.urlopen(BASE + path))['count']


def counts():
    return {name: count(f'/api/v1/{name}/')
            for name in ['sources', 'governance-metrics', 'trust-scores', 'validations', 'reconciliations']}


def run_checks():
    results = []

    def check(name, ok, info=''):
        results.append(ok)
        print(('PASS ' if ok else 'FAIL ') + name + (f'  [{info}]' if info != '' else ''))

    anon = Browser()

    # Anonymous reads
    for path in ['/', '/sources/', '/governance/', '/semantic/', '/reconciliation/', '/lineage/', '/osi/',
                 '/api/', '/api/v1/', '/api/v1/sources/', '/api/schema/', '/api/docs/', '/admin/login/']:
        status, _, _ = anon.request('GET', path)
        check(f'GET {path}', status == 200, status)
    first_source = json.loads(anon.request('GET', '/api/v1/sources/')[2])['results'][0]['id']
    status, _, _ = anon.request('GET', f'/sources/{first_source}/')
    check('GET source detail', status == 200, status)
    status, headers, body = anon.request('GET', '/reconciliation/export.csv')
    check('CSV export', status == 200 and headers['Content-Type'] == 'text/csv' and b'also includes' in body,
          f'{len(body.splitlines())} lines')
    css = re.search(rb'href="(/static/[^"]+\.css)"', anon.request('GET', '/')[2]).group(1).decode()
    status, _, _ = anon.request('GET', css)
    check(f'static CSS {css}', status == 200, status)

    # Anonymous writes are blocked
    metrics_before = count('/api/v1/governance-metrics/')
    status, headers, _ = anon.request('POST', '/governance/', {'name': 'anon', 'display_name': 'Anon',
                                                               'csrfmiddlewaretoken': anon.cookies.get('csrftoken', '')})
    check('anonymous form POST redirects to login', status == 302 and '/api/auth/login/' in headers['Location'], status)
    status, _, _ = anon.request('POST', '/api/v1/sources/', b'{}', {'Content-Type': 'application/json'})
    check('anonymous API POST rejected', status == 403, status)
    check('anonymous writes created nothing', count('/api/v1/governance-metrics/') == metrics_before)

    # Logged-in browser
    user = Browser()
    status, _, _ = user.login()
    check('login', status == 302 and 'sessionid' in user.cookies, status)
    check('sidebar shows user', f'Log out ({USER})'.encode() in user.request('GET', '/')[2])
    token = user.cookies['csrftoken']
    name = f'e2e_{time.time_ns()}'
    form = {'name': name, 'display_name': 'E2E Metric', 'formula': "SUM(x) WHERE y = 'z'",
            'data_type': 'numeric', 'csrfmiddlewaretoken': token}
    status, _, _ = user.request('POST', '/governance/', form, {'Referer': BASE + '/governance/'})
    check('form POST creates metric', status == 302 and count('/api/v1/governance-metrics/') == metrics_before + 1, status)
    status, _, body = user.request('POST', '/governance/', form, {'Referer': BASE + '/governance/'})
    check('duplicate metric name shows error', status == 200 and b'already exists' in body, status)
    runs_before = count('/api/v1/reconciliations/')
    status, _, _ = user.request('POST', '/reconciliation/run/', {'csrfmiddlewaretoken': token},
                                {'Referer': BASE + '/reconciliation/'})
    check('run reconciliation from UI', status == 302 and count('/api/v1/reconciliations/') > runs_before, status)

    # Behind a TLS-terminating proxy (Render/Heroku/Fly): browser Origin is https
    https_origin = BASE.replace('http://', 'https://', 1)
    status, _, _ = Browser({'X-Forwarded-Proto': 'https'}).login(origin=https_origin)
    check('login behind HTTPS proxy', status == 302, status)

    # API with Basic auth
    def basic(password):
        return {'Content-Type': 'application/json',
                'Authorization': 'Basic ' + base64.b64encode(f'{USER}:{password}'.encode()).decode()}
    payload = json.dumps({'name': f'E2E Source {time.time_ns()}', 'source_type': 'database'}).encode()
    status, _, _ = Browser().request('POST', '/api/v1/sources/', payload, basic(PASSWORD))
    check('API POST with Basic auth', status == 201, status)
    status, _, _ = Browser().request('POST', '/api/v1/sources/', payload, basic('wrong-password'))
    check('API POST with wrong password rejected', status in (401, 403), status)

    print(f'{sum(results)}/{len(results)} checks passed')
    return all(results)


if __name__ == '__main__':
    if sys.argv[1:] == ['counts']:
        print(json.dumps(counts(), sort_keys=True))
    else:
        if not PASSWORD:
            sys.exit('Set E2E_PASSWORD to the admin password')
        sys.exit(0 if run_checks() else 1)
