"""Tests of the user detail view in allocations/views/user_management_views.py."""

from django.test import TestCase
from django.urls import reverse

from allocations.tests.helpers import (
    create_superuser,
    create_user,
)
from allocations.tests.views.superuser_view_tests import SuperuserOnlyViewTests


class UserDetailViewTestCase(SuperuserOnlyViewTests, TestCase):
    """Tests of the page showing the details of one user."""

    def setUp(self):
        self.superuser = create_superuser()
        self.user = create_user()
        self.url = reverse('user_detail', args=[self.user.id])
        self.client.force_login(self.superuser)

    def test_user_detail_url(self):
        self.assertEqual(self.url, f'/users/{self.user.id}/')

    def test_get_user_detail(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user_detail.html')
        self.assertEqual(response.context['shown_user'], self.user)

    def test_page_shows_all_details(self):
        response = self.client.get(self.url)
        self.assertContains(response, '<dd>johndoe</dd>')
        self.assertContains(response, '<dd>John</dd>')
        self.assertContains(response, '<dd>Doe</dd>')
        self.assertContains(response, '<dd>johndoe@example.org</dd>')
        self.assertContains(response, '<dd>No</dd>')

    def test_page_shows_superuser_status(self):
        response = self.client.get(reverse('user_detail', args=[self.superuser.id]))
        self.assertContains(response, '<dd>Yes</dd>')

    def test_page_does_not_show_password(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, self.user.password)

    def test_page_links_to_update_delete_and_list(self):
        response = self.client.get(self.url)
        self.assertContains(response, reverse('user_update', args=[self.user.id]))
        self.assertContains(response, reverse('user_delete', args=[self.user.id]))
        self.assertContains(response, reverse('user_list'))

    def test_unknown_user_gives_404(self):
        response = self.client.get(reverse('user_detail', args=[9999]))
        self.assertEqual(response.status_code, 404)
