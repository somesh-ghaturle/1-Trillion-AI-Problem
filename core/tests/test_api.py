from django.test import TestCase, Client
import os


class APITest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_get_governance(self):
        resp = self.client.get('/api/governance/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('data_dictionary', data)

    def test_post_validate_uses_sample(self):
        resp = self.client.post('/api/validate/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('score', data)
        self.assertIn('results', data)
        self.assertIsInstance(data['results'], list)

    def test_post_trust_uses_sample(self):
        resp = self.client.post('/api/trust/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('trust_score', data)
        self.assertIn('overall_score', data['trust_score'])

    def test_admin_token_enforcement(self):
        # Set ADMIN_TOKEN and verify unauthenticated requests are forbidden
        os.environ['ADMIN_TOKEN'] = 'testsecret'

        try:
            resp_no_auth = self.client.post('/api/validate/')
            self.assertEqual(resp_no_auth.status_code, 403)

            # With correct Bearer token
            resp_auth = self.client.post('/api/validate/', HTTP_AUTHORIZATION='Bearer testsecret')
            self.assertEqual(resp_auth.status_code, 200)
        finally:
            del os.environ['ADMIN_TOKEN']
