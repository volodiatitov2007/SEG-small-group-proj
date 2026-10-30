from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from allocations.tests.helpers import create_superuser, create_user

TEMPLATES_FOLDER = Path(settings.BASE_DIR) / 'allocations' / 'templates'


class BaseTemplateTestCase(TestCase):
    """Tests of the layout and menu that all pages share."""

    def setUp(self):
        self.user = create_user()
        self.superuser = create_superuser()

    def page_urls(self):
        """The URL of every page of the application."""
        return [
            reverse('dashboard'),
            reverse('profile'),
            reverse('password'),
            reverse('user_list'),
            reverse('user_create'),
            reverse('user_detail', args=[self.user.id]),
            reverse('user_update', args=[self.user.id]),
            reverse('user_delete', args=[self.user.id]),
        ]

    def test_logged_out_pages_extend_base_template(self):
        for url in [reverse('home'), reverse('log_in')]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertTemplateUsed(response, 'base.html')

    def test_logged_in_pages_extend_base_template(self):
        self.client.force_login(self.superuser)
        for url in self.page_urls():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertTemplateUsed(response, 'base.html')

    def test_pages_use_bootstrap_css(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'bootstrap.min.css')

    def test_pages_do_not_contain_javascript(self):
        self.client.force_login(self.superuser)
        for url in self.page_urls():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertNotContains(response, '<script')

    def test_templates_do_not_contain_javascript(self):
        for template in TEMPLATES_FOLDER.rglob('*.html'):
            with self.subTest(template=template.name):
                self.assertNotIn('<script', template.read_text())

    def test_application_has_no_javascript_files(self):
        app_folder = Path(settings.BASE_DIR) / 'allocations'
        self.assertEqual(list(app_folder.rglob('*.js')), [])

    # The menu

    def test_menu_when_logged_out(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, f'href="{reverse("log_in")}"')
        self.assertNotContains(response, f'href="{reverse("dashboard")}"')
        self.assertNotContains(response, f'href="{reverse("profile")}"')
        self.assertNotContains(response, f'href="{reverse("password")}"')
        self.assertNotContains(response, f'href="{reverse("user_list")}"')
        self.assertNotContains(response, 'Log out')

    def test_menu_of_normal_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, f'href="{reverse("dashboard")}"')
        self.assertContains(response, f'href="{reverse("profile")}"')
        self.assertContains(response, f'href="{reverse("password")}"')
        self.assertContains(response, 'Log out')
        self.assertNotContains(response, f'href="{reverse("user_list")}"')
        self.assertNotContains(response, f'href="{reverse("log_in")}"')

    def test_menu_of_superuser_also_has_users_option(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, f'href="{reverse("dashboard")}"')
        self.assertContains(response, f'href="{reverse("profile")}"')
        self.assertContains(response, f'href="{reverse("password")}"')
        self.assertContains(response, f'href="{reverse("user_list")}"')
        self.assertContains(response, 'Log out')

    def test_log_out_menu_option_is_a_post_form(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, f'<form method="post" action="{reverse("log_out")}">')
        self.assertContains(response, 'csrfmiddlewaretoken')

    # Messages

    def test_success_message_is_shown_as_success_alert(self):
        self.client.force_login(self.user)
        data = {
            'username': 'johndoe',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'johndoe@example.org',
        }
        response = self.client.post(reverse('profile'), data, follow=True)
        self.assertContains(response, '<div class="alert alert-success">Your profile has been updated.</div>')

    def test_error_message_is_shown_as_danger_alert(self):
        self.client.force_login(self.superuser)
        url = reverse('user_delete', args=[self.superuser.id])
        response = self.client.post(url, follow=True)
        self.assertContains(response, '<div class="alert alert-danger">You cannot delete your own account.</div>')

    def test_message_is_only_shown_once(self):
        self.client.force_login(self.superuser)
        self.client.post(reverse('user_delete', args=[self.superuser.id]), follow=True)
        response = self.client.get(reverse('dashboard'))
        self.assertNotContains(response, 'alert')
