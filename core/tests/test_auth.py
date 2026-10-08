from django.contrib.auth.models import User
from core.tests import make_editor
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from core.models import DataSource, GovernanceMetric, TrustScore


class AnonymousWriteTest(TestCase):
    def test_pages_readable_anonymously(self):
        self.assertEqual(self.client.get(reverse('governance_metrics')).status_code, 200)
        self.assertEqual(APIClient().get('/api/v1/sources/').status_code, 200)

    def test_view_post_redirects_to_login(self):
        resp = self.client.post(reverse('governance_metrics'), {'name': 'x', 'display_name': 'X'})
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('rest_framework:login'), resp['Location'])
        self.assertFalse(GovernanceMetric.objects.exists())

    def test_api_write_rejected(self):
        resp = APIClient().post('/api/v1/sources/', {'name': 'x', 'source_type': 'database'})
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(DataSource.objects.exists())

    def test_logged_in_post_allowed(self):
        self.client.force_login(make_editor())
        self.client.post(reverse('governance_metrics'), {'name': 'x', 'display_name': 'X'})
        self.assertTrue(GovernanceMetric.objects.filter(name='x').exists())

    def test_duplicate_metric_name_shows_error(self):
        self.client.force_login(make_editor())
        self.client.post(reverse('governance_metrics'), {'name': 'x', 'display_name': 'X'})
        resp = self.client.post(reverse('governance_metrics'), {'name': 'x', 'display_name': 'X2'})
        self.assertContains(resp, 'already exists')
        self.assertEqual(GovernanceMetric.objects.filter(name='x').count(), 1)


class SeedIdempotencyTest(TestCase):
    def test_second_seed_adds_nothing(self):
        call_command('seed_data', stdout=open('/dev/null', 'w'))
        before = TrustScore.objects.count()
        call_command('seed_data', stdout=open('/dev/null', 'w'))
        self.assertEqual(TrustScore.objects.count(), before)


class RolesTest(TestCase):
    """Viewer = logged in without Editor group: read-only. Editor/superuser can write."""

    def test_editor_group_has_core_permissions(self):
        from django.contrib.auth.models import Group
        perms = set(Group.objects.get(name='Editor').permissions.values_list('codename', flat=True))
        self.assertTrue({'add_governancemetric', 'delete_datasource', 'add_reconciliationrun'} <= perms)

    def test_viewer_form_post_forbidden(self):
        self.client.force_login(User.objects.create_user('viewer'))
        self.assertEqual(self.client.get(reverse('governance_metrics')).status_code, 200)
        resp = self.client.post(reverse('governance_metrics'), {'name': 'x', 'display_name': 'X'})
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(GovernanceMetric.objects.exists())

    def test_viewer_api_write_forbidden(self):
        client = APIClient()
        client.force_authenticate(User.objects.create_user('viewer'))
        self.assertEqual(client.get('/api/v1/sources/').status_code, 200)
        self.assertEqual(client.post('/api/v1/sources/', {'name': 'x', 'source_type': 'database'}).status_code, 403)
        self.assertEqual(client.post('/api/v1/reconciliations/run/').status_code, 403)

    def test_superuser_can_write(self):
        client = APIClient()
        client.force_authenticate(User.objects.create_superuser('root', password='pw'))
        self.assertEqual(client.post('/api/v1/sources/', {'name': 'x', 'source_type': 'database'}).status_code, 201)


class TokenAuthTest(TestCase):
    def test_obtain_and_use_token(self):
        from core.tests import make_editor
        user = make_editor('tokenuser')
        user.set_password('pw')
        user.save()
        resp = APIClient().post('/api/auth/token/', {'username': 'tokenuser', 'password': 'pw'})
        self.assertEqual(resp.status_code, 200)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token ' + resp.data['token'])
        self.assertEqual(client.post('/api/v1/sources/', {'name': 'x', 'source_type': 'database'}).status_code, 201)

    def test_bad_credentials_and_bad_token_rejected(self):
        User.objects.create_user('u', password='pw')
        self.assertEqual(APIClient().post('/api/auth/token/', {'username': 'u', 'password': 'nope'}).status_code, 400)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token not-a-real-token')
        self.assertIn(client.post('/api/v1/sources/', {'name': 'x'}).status_code, (401, 403))

    def test_token_endpoint_throttled(self):
        from django.core.cache import cache
        cache.clear()
        statuses = [APIClient().post('/api/auth/token/', {'username': 'x', 'password': 'y'}).status_code
                    for _ in range(11)]
        cache.clear()
        self.assertEqual(statuses[-1], 429)
        self.assertNotIn(429, statuses[:10])


class ThrottleBypassTest(TestCase):
    def tearDown(self):
        from django.core.cache import cache
        cache.clear()

    def hammer(self, forwarded_for):
        from django.core.cache import cache
        cache.clear()
        return [APIClient().post('/api/auth/token/', {'username': 'x', 'password': 'y'},
                                 HTTP_X_FORWARDED_FOR=forwarded_for(i)).status_code for i in range(11)]

    def test_rotating_forwarded_for_without_proxy_still_throttled(self):
        from django.test import override_settings
        from django.conf import settings
        with override_settings(REST_FRAMEWORK={**settings.REST_FRAMEWORK, 'NUM_PROXIES': 0}):
            self.assertEqual(self.hammer(lambda i: f'203.0.113.{i}')[-1], 429)

    def test_rotating_spoofed_prefix_behind_proxy_still_throttled(self):
        # Proxy appends the real client IP last; attacker controls only the earlier entries
        from django.test import override_settings
        from django.conf import settings
        with override_settings(REST_FRAMEWORK={**settings.REST_FRAMEWORK, 'NUM_PROXIES': 1}):
            self.assertEqual(self.hammer(lambda i: f'203.0.113.{i}, 198.51.100.7')[-1], 429)

    def test_basic_auth_not_accepted(self):
        import base64
        User.objects.create_superuser('root', password='pw')
        resp = APIClient().post('/api/v1/sources/', {'name': 'x', 'source_type': 'database'},
                                HTTP_AUTHORIZATION='Basic ' + base64.b64encode(b'root:pw').decode())
        self.assertIn(resp.status_code, (401, 403))


class LoginLockoutTest(TestCase):
    """django-axes: 5 failures for a username from one IP lock that pair out for 15 minutes."""

    def setUp(self):
        User.objects.create_user('alice', password='right-password')

    def login(self, password, ip='198.51.100.1'):
        return self.client.post(reverse('rest_framework:login'),
                                {'username': 'alice', 'password': password}, REMOTE_ADDR=ip)

    def test_locked_after_five_failures_even_with_right_password(self):
        for _ in range(5):
            self.login('wrong')
        resp = self.login('right-password')
        self.assertEqual(resp.status_code, 429)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_other_ip_not_locked(self):
        for _ in range(5):
            self.login('wrong')
        self.assertEqual(self.login('right-password', ip='198.51.100.2').status_code, 302)

    def test_success_resets_failures(self):
        for _ in range(4):
            self.login('wrong')
        self.assertEqual(self.login('right-password').status_code, 302)
        self.client.logout()
        for _ in range(4):
            self.login('wrong')
        self.assertEqual(self.login('right-password').status_code, 302)

    def test_token_endpoint_shares_lockout(self):
        from django.core.cache import cache
        cache.clear()
        for _ in range(5):
            self.login('wrong')
        resp = APIClient().post('/api/auth/token/', {'username': 'alice', 'password': 'right-password'},
                                REMOTE_ADDR='198.51.100.1')
        cache.clear()
        # Refused with DRF's generic 400 (axes' 429 page only wraps plain Django views); no token issued
        self.assertEqual(resp.status_code, 400)
        self.assertNotIn('token', resp.data)

    def test_spoofed_forwarded_for_does_not_dodge_lockout(self):
        for i in range(5):
            self.client.post(reverse('rest_framework:login'), {'username': 'alice', 'password': 'wrong'},
                             REMOTE_ADDR='198.51.100.1', HTTP_X_FORWARDED_FOR=f'203.0.113.{i}')
        self.assertEqual(self.login('right-password').status_code, 429)


class ApiRateLimitTest(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    tearDown = setUp

    def rates(self, anon, user):
        # DRF copies the rates into a class attribute at import, so override_settings can't reach them
        from unittest import mock
        from rest_framework.throttling import SimpleRateThrottle
        return mock.patch.object(SimpleRateThrottle, 'THROTTLE_RATES',
                                 {**SimpleRateThrottle.THROTTLE_RATES, 'anon': anon, 'user': user})

    def test_anonymous_limited_then_429_with_retry_after(self):
        with self.rates('3/min', '100/min'):
            codes = [APIClient().get('/api/v1/sources/').status_code for _ in range(4)]
            resp = APIClient().get('/api/v1/sources/')
        self.assertEqual(codes, [200, 200, 200, 429])
        self.assertIn('Retry-After', resp)

    def test_authenticated_users_get_their_own_higher_limit(self):
        client = APIClient()
        client.force_authenticate(User.objects.create_user('u'))
        with self.rates('1/min', '5/min'):
            codes = [client.get('/api/v1/sources/').status_code for _ in range(5)]
        self.assertEqual(codes, [200] * 5)
