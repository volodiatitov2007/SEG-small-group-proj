"""Tests of the project views in allocations/views/project_views.py."""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from allocations.models import AllocationRun, Cohort, Project, Student, Team, TeamMembership
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


class ProjectUpdateViewTestCase(TestCase):
    """Tests of editing a project."""

    def setUp(self):
        self.user = create_user()
        self.project = Project.objects.create(name='SEG 2026', description='Old', owner=self.user)
        self.url = reverse('project_update', args=[self.project.id])
        self.client.force_login(self.user)

    def test_project_update_url(self):
        self.assertEqual(self.url, f'/projects/{self.project.id}/edit/')

    def test_logged_out_user_is_redirected_to_log_in(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertRedirects(response, log_in_url_for(self.url))

    def test_get_shows_the_form_filled_in(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'project_form.html')
        self.assertContains(response, 'Edit project')
        self.assertContains(response, 'value="SEG 2026"')

    def test_valid_form_updates_the_project(self):
        self.client.post(self.url, {'name': 'SEG 2027', 'description': 'New'})
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, 'SEG 2027')
        self.assertEqual(self.project.description, 'New')
        self.assertEqual(Project.objects.count(), 1)

    def test_valid_form_redirects_to_the_project_with_a_message(self):
        response = self.client.post(self.url, {'name': 'SEG 2027'}, follow=True)
        self.assertRedirects(response, reverse('project_detail', args=[self.project.id]))
        self.assertIn('Project SEG 2027 has been updated.', messages_in(response))

    def test_blank_name_is_rejected_and_the_project_is_unchanged(self):
        response = self.client.post(self.url, {'name': ''})
        self.assertContains(response, 'This field is required.')
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, 'SEG 2026')

    def test_other_users_project_gives_404(self):
        other_project = Project.objects.create(name='Theirs', owner=create_superuser())
        response = self.client.get(reverse('project_update', args=[other_project.id]))
        self.assertEqual(response.status_code, 404)

    def test_missing_project_gives_404(self):
        response = self.client.get(reverse('project_update', args=[999]))
        self.assertEqual(response.status_code, 404)


class ProjectDeleteViewTestCase(TestCase):
    """Tests of deleting a project."""

    def setUp(self):
        self.user = create_user()
        self.project = Project.objects.create(name='SEG 2026', owner=self.user)
        self.url = reverse('project_delete', args=[self.project.id])
        self.client.force_login(self.user)

    def test_project_delete_url(self):
        self.assertEqual(self.url, f'/projects/{self.project.id}/delete/')

    def test_logged_out_user_is_redirected_to_log_in(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertRedirects(response, log_in_url_for(self.url))

    def test_get_shows_the_confirm_page_and_does_not_delete(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'project_confirm_delete.html')
        self.assertContains(response, 'SEG 2026')
        self.assertTrue(Project.objects.filter(id=self.project.id).exists())

    def test_post_deletes_the_project(self):
        self.client.post(self.url)
        self.assertFalse(Project.objects.filter(id=self.project.id).exists())

    def test_post_redirects_to_the_list_with_a_message(self):
        response = self.client.post(self.url, follow=True)
        self.assertRedirects(response, reverse('project_list'))
        self.assertIn('Project SEG 2026 has been deleted.', messages_in(response))

    def test_post_also_deletes_cohorts_students_and_runs(self):
        cohort = Cohort.objects.create(project=self.project, original_filename='cohort.csv')
        student = Student.objects.create(cohort=cohort, first_name='Amira', last_name='Khan', email='amira@example.com')
        run = AllocationRun.objects.create(project=self.project, cohort=cohort, status=AllocationRun.Status.OK)
        team = Team.objects.create(run=run, name='Team 1')
        TeamMembership.objects.create(team=team, student=student)
        self.client.post(self.url)
        self.assertEqual(Cohort.objects.count(), 0)
        self.assertEqual(Student.objects.count(), 0)
        self.assertEqual(AllocationRun.objects.count(), 0)
        self.assertEqual(TeamMembership.objects.count(), 0)

    def test_other_users_project_gives_404_and_is_not_deleted(self):
        other_project = Project.objects.create(name='Theirs', owner=create_superuser())
        response = self.client.post(reverse('project_delete', args=[other_project.id]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Project.objects.filter(id=other_project.id).exists())

    def test_missing_project_gives_404(self):
        response = self.client.get(reverse('project_delete', args=[999]))
        self.assertEqual(response.status_code, 404)
