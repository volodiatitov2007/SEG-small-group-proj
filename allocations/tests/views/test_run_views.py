from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from allocations.models import AllocationRun, Cohort, Project, Student
from allocations.tests.helpers import PASSWORD, create_user, log_in_url_for, messages_in


class StartRunViewTestCase(TestCase):
    def setUp(self):
        self.owner = create_user()
        self.other_user = create_user(username='other')
        self.project = Project.objects.create(name='Project', owner=self.owner)
        self.url = reverse('run_allocation', kwargs={'project_id': self.project.id})
        self.project_url = reverse('project_detail', kwargs={'project_id': self.project.id})

    def add_cohort(self, student_count=10, filename='students.csv'):
        cohort = Cohort.objects.create(project=self.project, original_filename=filename)
        for number in range(student_count):
            Student.objects.create(
                cohort=cohort, first_name=f'First{number}', last_name=f'Last{number}',
                email=f'{filename}-{number}@example.org',
            )
        return cohort

    def test_run_allocation_url(self):
        self.assertEqual(self.url, f'/projects/{self.project.id}/run/')

    def test_owner_post_creates_a_run_and_redirects_to_run_detail(self):
        cohort = self.add_cohort()
        self.client.login(username=self.owner.username, password=PASSWORD)
        response = self.client.post(self.url)
        run = AllocationRun.objects.get()
        self.assertRedirects(response, reverse('run_detail', kwargs={'run_id': run.id}))
        self.assertEqual(run.cohort, cohort)
        self.assertEqual(run.status, AllocationRun.Status.OK)

    def test_post_uses_the_latest_cohort(self):
        self.add_cohort(filename='old.csv')
        latest = self.add_cohort(filename='new.csv')
        self.client.login(username=self.owner.username, password=PASSWORD)
        self.client.post(self.url)
        self.assertEqual(AllocationRun.objects.get().cohort, latest)

    def test_unreadable_policy_shows_its_own_failure_not_infeasible_or_timeout(self):
        self.add_cohort()
        self.client.login(username=self.owner.username, password=PASSWORD)
        with patch('allocations.views.run_views.DEFAULT_RULES', [{'key': 'no_such_rule'}]):
            response = self.client.post(self.url, follow=True)
        self.assertEqual(AllocationRun.objects.get().status, AllocationRun.Status.BAD_POLICY)
        self.assertTemplateUsed(response, 'run_failed.html')
        self.assertContains(response, 'Policy cannot be read.')
        self.assertContains(response, 'no_such_rule')
        self.assertNotContains(response, 'Known impossible.')
        self.assertNotContains(response, 'time limit')

    def test_get_is_not_allowed_and_creates_no_run(self):
        self.add_cohort()
        self.client.login(username=self.owner.username, password=PASSWORD)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
        self.assertEqual(AllocationRun.objects.count(), 0)

    def test_another_users_project_is_404_and_creates_no_run(self):
        self.add_cohort()
        self.client.login(username=self.other_user.username, password=PASSWORD)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(AllocationRun.objects.count(), 0)

    def test_anonymous_post_redirects_to_log_in_and_creates_no_run(self):
        self.add_cohort()
        response = self.client.post(self.url)
        self.assertRedirects(response, log_in_url_for(self.url))
        self.assertEqual(AllocationRun.objects.count(), 0)

    def test_post_without_a_csrf_token_is_forbidden_and_creates_no_run(self):
        self.add_cohort()
        client = Client(enforce_csrf_checks=True)
        client.login(username=self.owner.username, password=PASSWORD)
        response = client.post(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(AllocationRun.objects.count(), 0)

    def test_project_without_a_cohort_redirects_to_project_detail_with_a_message_and_no_run(self):
        self.client.login(username=self.owner.username, password=PASSWORD)
        response = self.client.post(self.url, follow=True)
        self.assertRedirects(response, self.project_url)
        self.assertEqual(messages_in(response), ['Upload a cohort CSV before running an allocation.'])
        self.assertEqual(AllocationRun.objects.count(), 0)

    def test_project_detail_shows_the_run_allocation_button_with_a_csrf_token(self):
        self.client.login(username=self.owner.username, password=PASSWORD)
        response = self.client.get(self.project_url)
        self.assertContains(response, 'Run allocation')
        self.assertContains(response, f'action="{self.url}"')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
