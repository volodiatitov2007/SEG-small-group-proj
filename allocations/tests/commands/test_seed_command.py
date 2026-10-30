from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from allocations.models import User


class SeedCommandTestCase(TestCase):
    """Tests of the "python manage.py seed" command."""

    def seed(self):
        output = StringIO()
        call_command('seed', stdout=output)
        return output.getvalue()

    def test_seed_creates_102_users(self):
        self.seed()
        self.assertEqual(User.objects.count(), 102)

    def test_seed_creates_superuser_janedoe(self):
        self.seed()
        user = User.objects.get(username='janedoe')
        self.assertEqual(user.get_full_name(), 'Jane Doe')
        self.assertEqual(user.email, 'janedoe@example.org')
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.check_password('Allocation123'))

    def test_seed_creates_normal_user_johndoe(self):
        self.seed()
        user = User.objects.get(username='johndoe')
        self.assertEqual(user.get_full_name(), 'John Doe')
        self.assertEqual(user.email, 'johndoe@example.org')
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)
        self.assertTrue(user.check_password('Allocation123'))

    def test_janedoe_is_the_only_superuser(self):
        self.seed()
        superusers = User.objects.filter(is_superuser=True)
        self.assertEqual([user.username for user in superusers], ['janedoe'])

    def test_only_superusers_are_staff(self):
        self.seed()
        staff = User.objects.filter(is_staff=True)
        self.assertEqual([user.username for user in staff], ['janedoe'])

    def test_seed_creates_sample_users(self):
        self.seed()
        user = User.objects.get(username='alice.ahmed')
        self.assertEqual(user.first_name, 'Alice')
        self.assertEqual(user.last_name, 'Ahmed')
        self.assertEqual(user.email, 'alice.ahmed@example.org')
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password('Allocation123'))

    def test_seeded_users_are_valid(self):
        self.seed()
        for user in User.objects.all():
            user.full_clean()

    def test_seeding_twice_does_not_create_duplicates(self):
        self.seed()
        self.seed()
        self.assertEqual(User.objects.count(), 102)

    def test_seed_keeps_existing_users(self):
        User.objects.create_user(
            username='alicechen',
            first_name='Alice',
            last_name='Chen',
            email='alicechen@example.org',
            password='Allocation123',
        )
        self.seed()
        self.assertEqual(User.objects.count(), 103)

    def test_seed_reports_how_to_log_in(self):
        output = self.seed()
        self.assertIn('The database now contains 102 users.', output)
        self.assertIn('janedoe', output)
        self.assertIn('johndoe', output)
        self.assertIn('Allocation123', output)
