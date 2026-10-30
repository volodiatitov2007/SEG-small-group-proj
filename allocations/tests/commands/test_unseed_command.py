from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from allocations.models import User


class UnseedCommandTestCase(TestCase):
    """Tests of the "python manage.py unseed" command."""

    def unseed(self):
        output = StringIO()
        call_command('unseed', stdout=output)
        return output.getvalue()

    def test_unseed_deletes_all_users(self):
        call_command('seed', stdout=StringIO())
        output = self.unseed()
        self.assertEqual(User.objects.count(), 0)
        self.assertIn('Deleted 102 users.', output)

    def test_unseed_on_empty_database(self):
        output = self.unseed()
        self.assertEqual(User.objects.count(), 0)
        self.assertIn('Deleted 0 users.', output)
