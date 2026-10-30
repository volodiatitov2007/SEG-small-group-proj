"""Tests of the password view in allocations/views/user_management_views.py."""

from django.test import TestCase
from django.urls import reverse

from allocations.forms import PasswordForm
from allocations.tests.helpers import (
    PASSWORD,
    create_user,
    log_in_url_for,
    logged_in_user_id,
    messages_in,
)


class PasswordViewTestCase(TestCase):
    """Tests of the view where users change their own password."""

    def setUp(self):
        self.url = reverse('password')
        self.user = create_user()
        self.data = {
            'old_password': PASSWORD,
            'new_password': 'NewPassword456',
            'new_password_confirmation': 'NewPassword456',
        }

    def test_password_url(self):
        self.assertEqual(self.url, '/password/')

    def test_get_password_requires_log_in(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, log_in_url_for(self.url))

    def test_post_password_requires_log_in(self):
        response = self.client.post(self.url, self.data)
        self.assertRedirects(response, log_in_url_for(self.url))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_get_password(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'password.html')
        self.assertIsInstance(response.context['form'], PasswordForm)

    def test_successful_password_change(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, self.data, follow=True)
        self.assertRedirects(response, reverse('dashboard'))
        self.assertIn('Your password has been changed.', messages_in(response))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPassword456'))

    def test_user_stays_logged_in_after_changing_password(self):
        self.client.force_login(self.user)
        self.client.post(self.url, self.data)
        self.assertEqual(logged_in_user_id(self.client), self.user.id)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_user_can_log_in_with_new_password_but_not_old_one(self):
        self.client.force_login(self.user)
        self.client.post(self.url, self.data)
        self.client.logout()
        self.assertFalse(self.client.login(username='johndoe', password=PASSWORD))
        self.assertTrue(self.client.login(username='johndoe', password='NewPassword456'))

    def test_password_change_with_wrong_old_password(self):
        self.client.force_login(self.user)
        self.data['old_password'] = 'WrongPassword123'
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'password.html')
        self.assertIn('old_password', response.context['form'].errors)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_password_change_with_different_confirmation(self):
        self.client.force_login(self.user)
        self.data['new_password_confirmation'] = 'OtherPassword789'
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_password_change_with_weak_password(self):
        self.client.force_login(self.user)
        self.data['new_password'] = 'Password123'
        self.data['new_password_confirmation'] = 'Password123'
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_passwords_are_not_shown_again_after_error(self):
        self.client.force_login(self.user)
        self.data['new_password_confirmation'] = 'OtherPassword789'
        response = self.client.post(self.url, self.data)
        self.assertNotContains(response, PASSWORD)
        self.assertNotContains(response, 'NewPassword456')
