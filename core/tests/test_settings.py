from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from trustsite.settings import database_from_url


class DatabaseFromUrlTest(SimpleTestCase):
    def test_full_url(self):
        db = database_from_url('postgres://u%40corp:p%2Fw@db.example.com:6543/trust?sslmode=require')
        self.assertEqual(db['ENGINE'], 'django_prometheus.db.backends.postgresql')
        self.assertEqual(
            (db['NAME'], db['USER'], db['PASSWORD'], db['HOST'], db['PORT']),
            ('trust', 'u@corp', 'p/w', 'db.example.com', '6543'),
        )
        self.assertEqual(db['OPTIONS'], {'sslmode': 'require'})

    def test_default_port(self):
        self.assertEqual(database_from_url('postgresql://u:p@db/trust')['PORT'], '')

    def test_rejects_other_schemes(self):
        with self.assertRaises(ImproperlyConfigured):
            database_from_url('mysql://u:p@db/trust')
