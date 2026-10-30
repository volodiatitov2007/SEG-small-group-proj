"""Tests of the user update view in allocations/views/user_management_views.py."""

from django.test import TestCase
from django.urls import reverse

from allocations.forms import UserUpdateForm
from allocations.tests.helpers import (
    PASSWORD,
    create_superuser,
    create_user,
    messages_in,
)
from allocations.tests.views.superuser_view_tests import SuperuserOnlyViewTests


class UserUpdateViewTestCase(SuperuserOnlyViewTests, TestCase):
    """Tests of the view where superusers update users."""

    def setUp(self):
        self.superuser = create_superuser()
        self.user = create_user()
        self.url = reverse('user_update', args=[self.user.id])
        self.client.force_login(self.superuser)
        self.data = {
            'username': 'johnny',
            'first_name': 'Johnny',
            'last_name': 'Dough',
            'email': 'johnny@example.org',
            'is_superuser': 'on',
        }

    def test_user_update_url(self):
        self.assertEqual(self.url, f'/users/{self.user.id}/update/')

    def test_get_user_update(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user_form.html')
        form = response.context['form']
        self.assertIsInstance(form, UserUpdateForm)
        self.assertEqual(form.instance, self.user)
        self.assertContains(response, 'Update user')

    def test_get_user_update_shows_current_details(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'value="johndoe"')
        self.assertContains(response, 'value="johndoe@example.org"')

    def test_successful_update(self):
        response = self.client.post(self.url, self.data, follow=True)
        self.assertRedirects(response, reverse('user_detail', args=[self.user.id]))
        self.assertIn('User johnny has been updated.', messages_in(response))
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'johnny')
        self.assertEqual(self.user.first_name, 'Johnny')
        self.assertEqual(self.user.last_name, 'Dough')
        self.assertEqual(self.user.email, 'johnny@example.org')
        self.assertTrue(self.user.is_superuser)

    def test_update_can_remove_superuser_status(self):
        other_superuser = create_user('alicechen', 'Alice', 'Chen', is_superuser=True)
        url = reverse('user_update', args=[other_superuser.id])
        del self.data['is_superuser']
        self.client.post(url, self.data)
        other_superuser.refresh_from_db()
        self.assertFalse(other_superuser.is_superuser)

    def test_update_does_not_change_password(self):
        self.client.post(self.url, self.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_unsuccessful_update(self):
        self.data['email'] = 'not an email'
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user_form.html')
        self.assertTrue(response.context['form'].errors)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'johndoe')

    def test_update_with_email_of_another_user(self):
        self.data['email'] = self.superuser.email
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'johndoe@example.org')

    def test_normal_user_cannot_update_user(self):
        self.client.force_login(self.user)
        self.client.post(self.url, self.data)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_superuser)
        self.assertEqual(self.user.username, 'johndoe')

    def test_unknown_user_gives_404(self):
        response = self.client.get(reverse('user_update', args=[9999]))
        self.assertEqual(response.status_code, 404)
