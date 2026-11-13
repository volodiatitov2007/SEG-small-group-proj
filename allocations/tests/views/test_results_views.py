import csv
from io import StringIO

from django.test import TestCase
from django.urls import reverse

from allocations.models import AllocationRun, Cohort, Project, Student, Team, TeamMembership
from allocations.tests.helpers import create_user, log_in_url_for


class ResultsViewsTestCase(TestCase):
    def setUp(self):
        self.owner = create_user()
        self.other_user = create_user(username='other')
        self.project = Project.objects.create(name='Group Allocation!', owner=self.owner)
        self.cohort = Cohort.objects.create(project=self.project, original_filename='students.csv')
        self.run = AllocationRun.objects.create(
            project=self.project, cohort=self.cohort, status=AllocationRun.Status.OK,
            violations=[{'team': 'Team 2', 'rule': 'balance'}],
        )
        self.team1 = Team.objects.create(run=self.run, name='Team 1')
        self.team2 = Team.objects.create(run=self.run, name='Team 2')
        self.student_a = Student.objects.create(
            cohort=self.cohort, first_name='Alice', last_name='Smith', email='alice@example.org',
        )
        self.student_b = Student.objects.create(
            cohort=self.cohort, first_name='Bob', last_name='Jones', email='bob@example.org',
        )
        TeamMembership.objects.create(team=self.team1, student=self.student_a)
        TeamMembership.objects.create(team=self.team2, student=self.student_b)

    def test_project_detail_lists_only_projects_owned_by_user(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('project_detail', args=[self.project.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['project'], self.project)
        self.assertQuerySetEqual(response.context['runs'], [self.run])

    def test_project_detail_requires_login_and_enforces_ownership(self):
        url = reverse('project_detail', args=[self.project.pk])
        response = self.client.get(url)
        self.assertRedirects(response, log_in_url_for(url))
        self.client.force_login(self.other_user)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_run_detail_shows_teams_counts_and_rule_violations(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('run_detail', args=[self.run.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['team_count'], 2)
        self.assertEqual(response.context['student_count'], 2)
        self.assertEqual(response.context['allocated_count'], 2)
        self.assertEqual(response.context['unmet_rules'], self.run.violations)
        teams = {team.name: team for team in response.context['teams']}
        self.assertFalse(teams['Team 1'].has_violation)
        self.assertTrue(teams['Team 2'].has_violation)

    def test_failed_run_shows_failure_page(self):
        self.run.status = AllocationRun.Status.INFEASIBLE
        self.run.message = 'No valid allocation was found.'
        self.run.save()
        self.client.force_login(self.owner)
        response = self.client.get(reverse('run_detail', args=[self.run.pk]))
        self.assertTemplateUsed(response, 'run_failed.html')
        self.assertEqual(response.context['run'].message, self.run.message)

    def test_run_detail_requires_owner_and_login(self):
        url = reverse('run_detail', args=[self.run.pk])
        self.assertRedirects(self.client.get(url), log_in_url_for(url))
        self.client.force_login(self.other_user)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_csv_export_contains_sorted_memberships_and_safe_filename(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('export_run_csv', args=[self.run.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertEqual(response['Content-Disposition'], f'attachment; filename="group-allocation-run-{self.run.pk}.csv"')
        rows = list(csv.reader(StringIO(response.content.decode('utf-8'))))
        self.assertEqual(rows, [
            ['first_name', 'last_name', 'email', 'team'],
            ['Bob', 'Jones', 'bob@example.org', 'Team 2'],
            ['Alice', 'Smith', 'alice@example.org', 'Team 1'],
        ])

    def test_csv_export_requires_owner_and_successful_run(self):
        url = reverse('export_run_csv', args=[self.run.pk])
        self.assertRedirects(self.client.get(url), log_in_url_for(url))
        self.client.force_login(self.other_user)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.owner)
        failed_run = AllocationRun.objects.create(
            project=self.project, cohort=self.cohort, status=AllocationRun.Status.TIMEOUT,
        )
        self.assertEqual(self.client.get(reverse('export_run_csv', args=[failed_run.pk])).status_code, 404)
