"""Tests of the views in allocations/views/session_views.py."""

from django.test import TestCase
from django.urls import reverse

from allocations.forms import LogInForm
from allocations.tests.helpers import PASSWORD, create_user, log_in_url_for, logged_in_user_id


class HomeViewTestCase(TestCase):
    """Tests of the home page."""

    def setUp(self):
        self.url = reverse('home')

    def test_home_url(self):
        self.assertEqual(self.url, '/')

    def test_get_home(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')

    def test_home_links_to_log_in(self):
        response = self.client.get(self.url)
        self.assertContains(response, f'href="{reverse("log_in")}"')

    def test_home_redirects_logged_in_user_to_dashboard(self):
        self.client.force_login(create_user())
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('dashboard'))


class LogInViewTestCase(TestCase):
    """Tests of the log in view."""

    def setUp(self):
        self.url = reverse('log_in')
        self.user = create_user()
        self.data = {'username': 'johndoe', 'password': PASSWORD}

    def test_log_in_url(self):
        self.assertEqual(self.url, '/log_in/')

    def test_get_log_in(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'log_in.html')
        self.assertIsInstance(response.context['form'], LogInForm)
        self.assertFalse(response.context['form'].is_bound)

    def test_successful_log_in(self):
        response = self.client.post(self.url, self.data)
        self.assertRedirects(response, reverse('dashboard'))
        self.assertEqual(logged_in_user_id(self.client), self.user.id)

    def test_successful_log_in_of_superuser(self):
        superuser = create_user('janedoe', 'Jane', 'Doe', is_superuser=True)
        self.data['username'] = 'janedoe'
        response = self.client.post(self.url, self.data)
        self.assertRedirects(response, reverse('dashboard'))
        self.assertEqual(logged_in_user_id(self.client), superuser.id)

    def test_log_in_with_wrong_password(self):
        self.data['password'] = 'WrongPassword123'
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'log_in.html')
        self.assertTrue(response.context['form'].errors)
        self.assertIsNone(logged_in_user_id(self.client))

    def test_log_in_with_unknown_username(self):
        self.data['username'] = 'nobody'
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(logged_in_user_id(self.client))

    def test_log_in_with_blank_fields(self):
        response = self.client.post(self.url, {'username': '', 'password': ''})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(logged_in_user_id(self.client))

    def test_inactive_user_cannot_log_in(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(logged_in_user_id(self.client))

    def test_unsuccessful_log_in_shows_an_error(self):
        self.data['password'] = 'WrongPassword123'
        response = self.client.post(self.url, self.data)
        self.assertContains(response, 'alert-danger')

    def test_unsuccessful_log_in_keeps_username_but_not_password(self):
        self.data['password'] = 'WrongPassword123'
        response = self.client.post(self.url, self.data)
        self.assertContains(response, 'value="johndoe"')
        self.assertNotContains(response, 'WrongPassword123')

    def test_get_log_in_redirects_logged_in_user_to_dashboard(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('dashboard'))

    def test_post_log_in_redirects_logged_in_user_to_dashboard(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, self.data)
        self.assertRedirects(response, reverse('dashboard'))


class LogOutViewTestCase(TestCase):
    """Tests of the log out view."""

    def setUp(self):
        self.url = reverse('log_out')
        self.user = create_user()

    def test_log_out_url(self):
        self.assertEqual(self.url, '/log_out/')

    def test_log_out(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('home'))
        self.assertIsNone(logged_in_user_id(self.client))

    def test_logged_out_user_can_no_longer_see_dashboard(self):
        self.client.force_login(self.user)
        self.client.post(self.url)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_log_out_does_not_accept_get(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
        self.assertEqual(logged_in_user_id(self.client), self.user.id)

    def test_log_out_when_not_logged_in(self):
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('home'))


class DashboardViewTestCase(TestCase):
    """Tests of the dashboard."""

    def setUp(self):
        self.url = reverse('dashboard')
        self.user = create_user()

    def test_dashboard_url(self):
        self.assertEqual(self.url, '/dashboard/')

    def test_dashboard_requires_log_in(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, log_in_url_for(self.url))

    def test_get_dashboard(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')

    def test_dashboard_greets_user(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, 'Welcome, John')
        self.assertContains(response, 'johndoe')
