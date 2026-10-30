"""Tests of the profile view in allocations/views/user_management_views.py."""

from django.test import TestCase
from django.urls import reverse

from allocations.forms import ProfileForm
from allocations.tests.helpers import (
    PASSWORD,
    create_user,
    log_in_url_for,
    messages_in,
)


class ProfileViewTestCase(TestCase):
    """Tests of the view where users edit their own profile."""

    def setUp(self):
        self.url = reverse('profile')
        self.user = create_user()
        self.data = {
            'username': 'johnny',
            'first_name': 'Johnny',
            'last_name': 'Dough',
            'email': 'johnny@example.org',
        }

    def test_profile_url(self):
        self.assertEqual(self.url, '/profile/')

    def test_get_profile_requires_log_in(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, log_in_url_for(self.url))

    def test_post_profile_requires_log_in(self):
        response = self.client.post(self.url, self.data)
        self.assertRedirects(response, log_in_url_for(self.url))
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'johndoe')

    def test_get_profile(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profile.html')
        form = response.context['form']
        self.assertIsInstance(form, ProfileForm)
        self.assertEqual(form.instance, self.user)

    def test_get_profile_shows_current_details(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, 'value="johndoe"')
        self.assertContains(response, 'value="John"')
        self.assertContains(response, 'value="Doe"')
        self.assertContains(response, 'value="johndoe@example.org"')

    def test_successful_profile_update(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, self.data, follow=True)
        self.assertRedirects(response, reverse('dashboard'))
        self.assertIn('Your profile has been updated.', messages_in(response))
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'johnny')
        self.assertEqual(self.user.first_name, 'Johnny')
        self.assertEqual(self.user.last_name, 'Dough')
        self.assertEqual(self.user.email, 'johnny@example.org')

    def test_user_stays_logged_in_after_changing_username(self):
        self.client.force_login(self.user)
        self.client.post(self.url, self.data)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_unsuccessful_profile_update(self):
        self.client.force_login(self.user)
        self.data['email'] = 'not an email'
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profile.html')
        self.assertTrue(response.context['form'].errors)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'johndoe')
        self.assertEqual(self.user.email, 'johndoe@example.org')

    def test_profile_update_with_username_of_another_user(self):
        create_user('janedoe', 'Jane', 'Doe')
        self.client.force_login(self.user)
        self.data['username'] = 'janedoe'
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'johndoe')

    def test_user_cannot_make_themselves_superuser(self):
        self.client.force_login(self.user)
        self.data['is_superuser'] = 'on'
        self.client.post(self.url, self.data)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_superuser)

    def test_profile_update_does_not_change_password(self):
        self.client.force_login(self.user)
        self.client.post(self.url, self.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_profile_only_changes_logged_in_user(self):
        other_user = create_user('janedoe', 'Jane', 'Doe')
        self.client.force_login(self.user)
        self.client.post(self.url, self.data)
        other_user.refresh_from_db()
        self.assertEqual(other_user.username, 'janedoe')
