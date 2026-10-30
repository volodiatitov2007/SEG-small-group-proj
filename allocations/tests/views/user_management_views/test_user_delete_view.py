"""Tests of the user delete view in allocations/views/user_management_views.py."""

from django.test import TestCase
from django.urls import reverse

from allocations.models import User
from allocations.tests.helpers import (
    create_superuser,
    create_user,
    messages_in,
)
from allocations.tests.views.superuser_view_tests import SuperuserOnlyViewTests


class UserDeleteViewTestCase(SuperuserOnlyViewTests, TestCase):
    """Tests of the view where superusers delete users."""

    def setUp(self):
        self.superuser = create_superuser()
        self.user = create_user()
        self.url = reverse('user_delete', args=[self.user.id])
        self.client.force_login(self.superuser)

    def user_exists(self, user):
        return User.objects.filter(id=user.id).exists()

    def test_user_delete_url(self):
        self.assertEqual(self.url, f'/users/{self.user.id}/delete/')

    def test_get_asks_for_confirmation(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user_confirm_delete.html')
        self.assertEqual(response.context['shown_user'], self.user)
        self.assertContains(response, 'John Doe (johndoe)')

    def test_get_does_not_delete_user(self):
        self.client.get(self.url)
        self.assertTrue(self.user_exists(self.user))

    def test_confirmation_page_posts_to_delete_url_and_can_be_cancelled(self):
        response = self.client.get(self.url)
        self.assertContains(response, f'<form method="post" action="{self.url}">')
        self.assertContains(response, reverse('user_detail', args=[self.user.id]))

    def test_post_deletes_user(self):
        response = self.client.post(self.url, follow=True)
        self.assertRedirects(response, reverse('user_list'))
        self.assertIn('User johndoe has been deleted.', messages_in(response))
        self.assertFalse(self.user_exists(self.user))

    def test_post_only_deletes_one_user(self):
        count_before = User.objects.count()
        self.client.post(self.url)
        self.assertEqual(User.objects.count(), count_before - 1)
        self.assertTrue(self.user_exists(self.superuser))

    def test_superuser_can_delete_another_superuser(self):
        other_superuser = create_user('alicechen', 'Alice', 'Chen', is_superuser=True)
        self.client.post(reverse('user_delete', args=[other_superuser.id]))
        self.assertFalse(self.user_exists(other_superuser))

    def test_superuser_cannot_delete_themselves(self):
        url = reverse('user_delete', args=[self.superuser.id])
        response = self.client.post(url, follow=True)
        self.assertRedirects(response, reverse('user_detail', args=[self.superuser.id]))
        self.assertIn('You cannot delete your own account.', messages_in(response))
        self.assertTrue(self.user_exists(self.superuser))

    def test_superuser_is_not_asked_to_confirm_deleting_themselves(self):
        url = reverse('user_delete', args=[self.superuser.id])
        response = self.client.get(url)
        self.assertRedirects(response, reverse('user_detail', args=[self.superuser.id]))

    def test_normal_user_cannot_delete_user(self):
        other_user = create_user('alicechen', 'Alice', 'Chen')
        self.client.force_login(self.user)
        self.client.post(reverse('user_delete', args=[other_user.id]))
        self.assertTrue(self.user_exists(other_user))

    def test_unknown_user_gives_404(self):
        response = self.client.post(reverse('user_delete', args=[9999]))
        self.assertEqual(response.status_code, 404)
