"""Tests of the project views in allocations/views/project_views.py."""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from allocations.models import Project
from allocations.tests.helpers import create_superuser, create_user, log_in_url_for, messages_in


class ProjectListViewTestCase(TestCase):
    """Tests of the list of the logged-in user's projects."""

    def setUp(self):
        self.url = reverse('project_list')
        self.user = create_user()
        self.other_user = create_superuser()
        self.client.force_login(self.user)

    def test_project_list_url(self):
        self.assertEqual(self.url, '/projects/')

    def test_logged_out_user_is_redirected_to_log_in(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertRedirects(response, log_in_url_for(self.url))

    def test_list_shows_the_users_own_projects(self):
        Project.objects.create(name='SEG 2026', owner=self.user)
        response = self.client.get(self.url)
        self.assertContains(response, 'SEG 2026')

    def test_list_hides_other_users_projects(self):
        Project.objects.create(name='Someone else', owner=self.other_user)
        response = self.client.get(self.url)
        self.assertNotContains(response, 'Someone else')

    def test_list_shows_newest_project_first(self):
        old = Project.objects.create(name='Old project', owner=self.user)
        new = Project.objects.create(name='New project', owner=self.user)
        Project.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=1))
        response = self.client.get(self.url)
        self.assertEqual(list(response.context['projects']), [new, old])

    def test_list_links_to_each_project(self):
        project = Project.objects.create(name='SEG 2026', owner=self.user)
        response = self.client.get(self.url)
        self.assertContains(response, reverse('project_detail', args=[project.id]))

    def test_empty_list_shows_a_message(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'No projects yet.')


class ProjectCreateViewTestCase(TestCase):
    """Tests of creating a project."""

    def setUp(self):
        self.url = reverse('project_create')
        self.user = create_user()
        self.client.force_login(self.user)

    def test_project_create_url(self):
        self.assertEqual(self.url, '/projects/new/')

    def test_logged_out_user_is_redirected_to_log_in(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertRedirects(response, log_in_url_for(self.url))

    def test_get_shows_the_form(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'project_form.html')
        self.assertContains(response, 'Create project')

    def test_valid_form_creates_a_project_owned_by_the_user(self):
        self.client.post(self.url, {'name': 'SEG 2026', 'description': 'Small group project'})
        project = Project.objects.get()
        self.assertEqual(project.name, 'SEG 2026')
        self.assertEqual(project.owner, self.user)

    def test_valid_form_redirects_to_the_new_project_with_a_message(self):
        response = self.client.post(self.url, {'name': 'SEG 2026'}, follow=True)
        project = Project.objects.get()
        self.assertRedirects(response, reverse('project_detail', args=[project.id]))
        self.assertIn('Project SEG 2026 has been created.', messages_in(response))

    def test_blank_name_is_rejected_and_nothing_is_saved(self):
        response = self.client.post(self.url, {'name': ''})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required.')
        self.assertEqual(Project.objects.count(), 0)

    def test_owner_cannot_be_chosen_through_the_form(self):
        other_user = create_superuser()
        self.client.post(self.url, {'name': 'SEG 2026', 'owner': other_user.id})
        self.assertEqual(Project.objects.get().owner, self.user)
