from django.contrib.auth.models import User
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
        self.client.force_login(User.objects.create_user('tester'))
        self.client.post(reverse('governance_metrics'), {'name': 'x', 'display_name': 'X'})
        self.assertTrue(GovernanceMetric.objects.filter(name='x').exists())


class SeedIdempotencyTest(TestCase):
    def test_second_seed_adds_nothing(self):
        call_command('seed_data', stdout=open('/dev/null', 'w'))
        before = TrustScore.objects.count()
        call_command('seed_data', stdout=open('/dev/null', 'w'))
        self.assertEqual(TrustScore.objects.count(), before)
