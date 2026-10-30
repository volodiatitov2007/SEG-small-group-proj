"""Tests of the user create view in allocations/views/user_management_views.py."""

from django.test import TestCase
from django.urls import reverse

from allocations.forms import UserCreateForm
from allocations.models import User
from allocations.tests.helpers import (
    create_superuser,
    create_user,
    logged_in_user_id,
    messages_in,
)
from allocations.tests.views.superuser_view_tests import SuperuserOnlyViewTests


class UserCreateViewTestCase(SuperuserOnlyViewTests, TestCase):
    """Tests of the view where superusers create users."""

    def setUp(self):
        self.url = reverse('user_create')
        self.superuser = create_superuser()
        self.user = create_user()
        self.client.force_login(self.superuser)
        self.data = {
            'username': 'alicechen',
            'first_name': 'Alice',
            'last_name': 'Chen',
            'email': 'alicechen@example.org',
            'password': 'Allocation123',
            'password_confirmation': 'Allocation123',
        }

    def test_user_create_url(self):
        self.assertEqual(self.url, '/users/create/')

    def test_get_user_create(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user_form.html')
        self.assertIsInstance(response.context['form'], UserCreateForm)
        self.assertContains(response, 'Create user')

    def test_successful_create(self):
        count_before = User.objects.count()
        response = self.client.post(self.url, self.data, follow=True)
        self.assertEqual(User.objects.count(), count_before + 1)
        new_user = User.objects.get(username='alicechen')
        self.assertRedirects(response, reverse('user_detail', args=[new_user.id]))
        self.assertIn('User alicechen has been created.', messages_in(response))
        self.assertEqual(new_user.first_name, 'Alice')
        self.assertEqual(new_user.last_name, 'Chen')
        self.assertEqual(new_user.email, 'alicechen@example.org')
        self.assertFalse(new_user.is_superuser)
        self.assertTrue(new_user.check_password('Allocation123'))

    def test_create_superuser(self):
        self.data['is_superuser'] = 'on'
        self.client.post(self.url, self.data)
        self.assertTrue(User.objects.get(username='alicechen').is_superuser)

    def test_new_user_can_log_in(self):
        self.client.post(self.url, self.data)
        self.client.logout()
        self.assertTrue(self.client.login(username='alicechen', password='Allocation123'))

    def test_superuser_stays_logged_in_as_themselves(self):
        self.client.post(self.url, self.data)
        self.assertEqual(logged_in_user_id(self.client), self.superuser.id)

    def test_create_with_different_password_confirmation(self):
        self.data['password_confirmation'] = 'OtherPassword456'
        count_before = User.objects.count()
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user_form.html')
        self.assertTrue(response.context['form'].errors)
        self.assertEqual(User.objects.count(), count_before)

    def test_create_with_existing_username(self):
        self.data['username'] = 'johndoe'
        count_before = User.objects.count()
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), count_before)

    def test_create_with_existing_email(self):
        self.data['email'] = 'johndoe@example.org'
        count_before = User.objects.count()
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), count_before)

    def test_normal_user_cannot_create_user(self):
        self.client.force_login(self.user)
        self.client.post(self.url, self.data)
        self.assertFalse(User.objects.filter(username='alicechen').exists())
