"""Tests of the user list view in allocations/views/user_management_views.py."""

from django.test import TestCase
from django.urls import reverse

from allocations.tests.helpers import (
    create_superuser,
    create_user,
)
from allocations.tests.views.superuser_view_tests import SuperuserOnlyViewTests


class UserListViewTestCase(SuperuserOnlyViewTests, TestCase):
    """Tests of the list of users."""

    def setUp(self):
        self.url = reverse('user_list')
        self.superuser = create_superuser()
        self.user = create_user()
        self.client.force_login(self.superuser)

    def create_users(self, count):
        for number in range(count):
            create_user(f'user{number:02}', 'User', f'Number{number:02}')

    def test_user_list_url(self):
        self.assertEqual(self.url, '/users/')

    def test_get_user_list(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user_list.html')

    def test_list_shows_details_of_users(self):
        response = self.client.get(self.url)
        for user in [self.user, self.superuser]:
            self.assertContains(response, user.username)
            self.assertContains(response, user.get_full_name())
            self.assertContains(response, user.email)

    def test_list_shows_which_users_are_superusers(self):
        response = self.client.get(self.url)
        self.assertContains(response, '<td>Yes</td>', count=1)
        self.assertContains(response, '<td>No</td>', count=1)

    def test_list_links_to_each_user(self):
        response = self.client.get(self.url)
        self.assertContains(response, reverse('user_detail', args=[self.user.id]))
        self.assertContains(response, reverse('user_detail', args=[self.superuser.id]))

    def test_list_links_to_create_user(self):
        response = self.client.get(self.url)
        self.assertContains(response, reverse('user_create'))

    def test_list_is_ordered_by_last_name_then_first_name(self):
        create_user('alicechen', 'Alice', 'Chen')
        create_user('alicesmith', 'Alice', 'Smith')
        response = self.client.get(self.url)
        usernames = [user.username for user in response.context['page']]
        self.assertEqual(usernames, ['alicechen', 'janedoe', 'johndoe', 'alicesmith'])

    def test_list_shows_10_users_per_page(self):
        self.create_users(23)  # 25 users in total
        response = self.client.get(self.url)
        self.assertEqual(len(response.context['page']), 10)
        self.assertContains(response, 'Page 1 of 3')

    def test_last_page_shows_remaining_users(self):
        self.create_users(23)
        response = self.client.get(self.url, {'page': 3})
        self.assertEqual(len(response.context['page']), 5)
        self.assertContains(response, 'Page 3 of 3')

    def test_pages_do_not_overlap(self):
        self.create_users(23)
        first_page = self.client.get(self.url, {'page': 1}).context['page']
        second_page = self.client.get(self.url, {'page': 2}).context['page']
        self.assertFalse(set(first_page) & set(second_page))

    def test_first_page_links_to_next_and_last_pages_only(self):
        self.create_users(23)
        response = self.client.get(self.url)
        self.assertContains(response, 'href="?page=2"')
        self.assertContains(response, 'href="?page=3"')
        self.assertNotContains(response, 'Previous')
        self.assertNotContains(response, 'First')

    def test_middle_page_links_to_all_neighbouring_pages(self):
        self.create_users(23)
        response = self.client.get(self.url, {'page': 2})
        for text in ['First', 'Previous', 'Next', 'Last']:
            self.assertContains(response, text)

    def test_last_page_links_to_first_and_previous_pages_only(self):
        self.create_users(23)
        response = self.client.get(self.url, {'page': 3})
        self.assertContains(response, 'href="?page=1"')
        self.assertContains(response, 'href="?page=2"')
        self.assertNotContains(response, 'Next')
        self.assertNotContains(response, '>Last<')

    def test_single_page_has_no_page_links(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Page 1 of 1')
        self.assertNotContains(response, '?page=')

    def test_page_number_that_is_too_high_shows_last_page(self):
        self.create_users(23)
        response = self.client.get(self.url, {'page': 99})
        self.assertEqual(response.context['page'].number, 3)

    def test_page_number_that_is_not_a_number_shows_first_page(self):
        self.create_users(23)
        response = self.client.get(self.url, {'page': 'abc'})
        self.assertEqual(response.context['page'].number, 1)
