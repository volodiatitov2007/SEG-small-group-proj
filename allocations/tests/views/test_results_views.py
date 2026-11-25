import csv
import re
from dataclasses import asdict
from io import StringIO

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from allocations.allocator import allocate
from allocations.csv_import import parse_code
from allocations.models import AllocationRun, Cohort, Project, Student, Team, TeamMembership
from allocations.policies import TeamSizeRule, student_view
from allocations.tests.helpers import create_user, log_in_url_for


class ResultsViewsTestCase(TestCase):
    def setUp(self):
        self.owner = create_user()
        self.other_user = create_user(username='other')
        self.project = Project.objects.create(name='Group Allocation!', owner=self.owner)
        self.cohort = Cohort.objects.create(project=self.project, original_filename='students.csv')
        self.violation_message = 'Team 2: c-score spread is 34 (target 20 or less).'
        self.policy_snapshot = {'team_size': 4, 'balance_c_score': True}
        self.run = AllocationRun.objects.create(
            project=self.project, cohort=self.cohort, status=AllocationRun.Status.OK,
            policy_snapshot=self.policy_snapshot,
            violations=[{
                'rule': 'c_score_balance', 'hard': False, 'priority': 1,
                'team': 'Team 2', 'message': self.violation_message, 'amount': 34,
            }],
        )
        self.team1 = Team.objects.create(run=self.run, name='Team 1')
        self.team2 = Team.objects.create(run=self.run, name='Team 2')
        self.team10 = Team.objects.create(run=self.run, name='Team 10')
        self.student_a = Student.objects.create(
            cohort=self.cohort, first_name='Alice', last_name='Smith', email='alice@example.org',
        )
        self.student_b = Student.objects.create(
            cohort=self.cohort, first_name='Bob', last_name='Jones', email='bob@example.org',
        )
        self.student_c = Student.objects.create(
            cohort=self.cohort, first_name='Zoe', last_name='Adams', email='zoe@example.org',
        )
        TeamMembership.objects.create(team=self.team1, student=self.student_a)
        TeamMembership.objects.create(team=self.team2, student=self.student_b)
        TeamMembership.objects.create(team=self.team10, student=self.student_c)

    def test_project_detail_lists_runs_for_owned_project(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('project_detail', args=[self.project.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['project'], self.project)
        self.assertQuerySetEqual(response.context['runs'], [self.run])
        self.assertEqual(response.context['runs'][0].team_count, 3)
        self.assertEqual(response.context['runs'][0].student_count, 3)
        self.assertContains(response, 'Team size: 4')

    def test_project_detail_requires_login_and_enforces_ownership(self):
        url = reverse('project_detail', args=[self.project.pk])
        response = self.client.get(url)
        self.assertRedirects(response, log_in_url_for(url))
        self.client.force_login(self.other_user)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_project_detail_shows_distinct_empty_states(self):
        self.client.force_login(self.owner)
        empty_project = Project.objects.create(name='Empty project', owner=self.owner)
        response = self.client.get(reverse('project_detail', args=[empty_project.pk]))
        self.assertContains(response, 'No cohort uploaded yet.')

        project_with_cohort = Project.objects.create(name='Cohort only', owner=self.owner)
        Cohort.objects.create(project=project_with_cohort, original_filename='empty-cohort.csv')
        response = self.client.get(reverse('project_detail', args=[project_with_cohort.pk]))
        self.assertContains(response, 'No allocation runs yet.')

    def test_project_detail_formats_rule_list_policy_snapshot(self):
        self.run.policy_snapshot = {'rules': [{
            'key': 'team_size', 'hard': True, 'priority': 1,
            'min_size': 4, 'max_size': 5,
        }]}
        self.run.save(update_fields=['policy_snapshot'])
        self.client.force_login(self.owner)
        response = self.client.get(reverse('project_detail', args=[self.project.pk]))
        self.assertContains(response, 'Team size:')
        self.assertContains(response, 'Min size 4')
        self.assertNotContains(response, "{'rules':")

    def test_run_detail_formats_plain_list_policy_snapshot(self):
        self.run.policy_snapshot = [{
            'key': 'team_size', 'hard': True, 'priority': 1,
            'min_size': 4, 'max_size': 5,
        }]
        self.run.save(update_fields=['policy_snapshot'])
        self.client.force_login(self.owner)
        response = self.client.get(reverse('run_detail', args=[self.run.pk]))
        self.assertContains(response, 'Team size: Min size 4, Max size 5 (hard, high priority)')
        self.assertNotContains(response, "{'key': 'team_size'")

    def test_run_detail_shows_teams_counts_and_rule_violations(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('run_detail', args=[self.run.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['team_count'], 3)
        self.assertEqual(response.context['student_count'], 3)
        self.assertEqual(response.context['allocated_count'], 3)
        self.assertContains(response, '3 of 3 students allocated')
        self.assertEqual(response.context['unmet_rules'], self.run.violations)
        self.assertContains(response, self.violation_message)
        self.assertContains(response, 'Team size: 4')
        teams = {team.name: team for team in response.context['teams']}
        self.assertEqual([team.name for team in response.context['teams']], ['Team 1', 'Team 2', 'Team 10'])
        self.assertFalse(teams['Team 1'].has_violation)
        self.assertTrue(teams['Team 2'].has_violation)
        self.assertFalse(teams['Team 10'].has_violation)

    def test_run_detail_warns_when_students_are_not_all_allocated(self):
        TeamMembership.objects.filter(team=self.team10, student=self.student_c).delete()
        self.client.force_login(self.owner)
        response = self.client.get(reverse('run_detail', args=[self.run.pk]))
        self.assertContains(response, '2 of 3 students allocated')
        self.assertContains(response, 'Some students were left out.')
        self.assertContains(response, 'text-danger')

    def test_failed_run_shows_failure_page(self):
        self.run.status = AllocationRun.Status.INFEASIBLE
        self.run.message = 'No valid allocation was found.'
        self.run.duration_seconds = 15.0
        self.run.save()
        self.client.force_login(self.owner)
        response = self.client.get(reverse('run_detail', args=[self.run.pk]))
        self.assertTemplateUsed(response, 'run_failed.html')
        self.assertEqual(response.context['run'].message, self.run.message)
        self.assertContains(response, self.run.message)
        self.assertContains(response, '15.0 seconds')

    def test_bad_policy_run_has_its_own_failure_message(self):
        self.run.status = 'bad_policy'
        self.run.message = 'The policy has an unknown rule.'
        self.run.save()
        self.client.force_login(self.owner)
        response = self.client.get(reverse('run_detail', args=[self.run.pk]))
        self.assertContains(response, 'Policy cannot be read.')
        self.assertContains(response, 'The policy has an unknown rule.')
        self.assertNotContains(response, 'Known infeasible.')
        self.assertNotContains(response, 'This does not prove that none exists.')

    def test_timeout_run_explains_that_search_failure_is_not_proof_of_impossibility(self):
        self.run.status = AllocationRun.Status.TIMEOUT
        self.run.message = 'Search stopped after the configured time limit.'
        self.run.duration_seconds = 15.0
        self.run.save()
        self.client.force_login(self.owner)
        response = self.client.get(reverse('run_detail', args=[self.run.pk]))
        self.assertContains(response, 'This does not prove that none exists.')
        self.assertContains(response, self.run.message)
        self.assertContains(response, '15.0 seconds')

    def test_violation_groups_put_hard_rules_first_and_sort_teams_naturally(self):
        self.run.violations = [
            {'rule': 'gender', 'hard': False, 'priority': 1, 'team': 'Team 10', 'message': 'Soft ten.'},
            {'rule': 'gender', 'hard': False, 'priority': 1, 'team': 'Team 2', 'message': 'Soft two.'},
            {'rule': 'team_size', 'hard': True, 'priority': 3, 'team': 'Team 10', 'message': 'Hard ten.'},
            {'rule': 'c_score', 'hard': False, 'priority': 2, 'team': 'Team 1', 'message': 'Medium one.'},
        ]
        self.run.save(update_fields=['violations'])
        self.client.force_login(self.owner)
        response = self.client.get(reverse('run_detail', args=[self.run.pk]))
        groups = response.context['unmet_rule_groups']
        self.assertContains(response, 'Soft two.')
        self.assertEqual([group['label'] for group in groups], [
            'Team size (hard) - Low priority',
            'Gender (soft) - High priority',
            'C score (soft) - Medium priority',
        ])
        self.assertEqual(
            [item['message'] for item in groups[1]['violations']],
            ['Soft two.', 'Soft ten.'],
        )

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
            ['Alice', 'Smith', 'alice@example.org', 'Team 1'],
            ['Bob', 'Jones', 'bob@example.org', 'Team 2'],
            ['Zoe', 'Adams', 'zoe@example.org', 'Team 10'],
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

    def test_real_allocator_run_with_300_sample_students_paginates_and_exports_each_once(self):
        sample_path = settings.BASE_DIR / 'allocations/tests/fixtures/csv/sample_student_cohort_data.csv'
        with sample_path.open(newline='', encoding='utf-8-sig') as sample_file:
            sample_students = list(csv.DictReader(sample_file))
        self.assertEqual(len(sample_students), 300)

        cohort = Cohort.objects.create(
            project=self.project,
            original_filename='sample_student_cohort_data.csv',
            columns=list(sample_students[0]),
        )
        Student.objects.bulk_create([
            Student(
                cohort=cohort,
                first_name=row['first_name'],
                last_name=row['last_name'],
                email=row['email'],
                gender=parse_code(row['gender']) if row['gender'].strip() else None,
                ethnicity=parse_code(row['ethnicity']) if row['ethnicity'].strip() else None,
                # Exercise the missing-score display path; blank c-scores import as None.
                c_score=None if number == 0 or not row['c-score'].strip() else int(row['c-score']),
                extra={key: row[key] for key in ('schedule', 'ambition') if key in row},
            )
            for number, row in enumerate(sample_students)
        ])
        students = list(cohort.students.order_by('pk'))
        rule = TeamSizeRule(min_size=4, max_size=5, hard=True)
        result = allocate([student_view(student) for student in students], [rule], max_steps=0)
        self.assertEqual(result.status, AllocationRun.Status.OK)
        def natural_key(value):
            return tuple(
                (0, int(part)) if part.isdigit() else (1, part.casefold())
                for part in re.split(r'(\d+)', value)
            )

        expected_team_names = sorted(result.teams, key=natural_key)
        team_count = len(result.teams)

        run = AllocationRun.objects.create(
            project=self.project,
            cohort=cohort,
            status=result.status,
            policy_snapshot={'rules': [rule.to_dict()]},
            violations=[asdict(violation) for violation in result.violations],
            duration_seconds=result.duration_seconds,
        )
        students_by_id = {student.pk: student for student in students}
        for team_name, members in result.teams.items():
            team = Team.objects.create(run=run, name=team_name)
            TeamMembership.objects.bulk_create([
                TeamMembership(team=team, student=students_by_id[member.id])
                for member in members
            ])

        self.client.force_login(self.owner)
        page_size = 50
        page_count = (team_count + page_size - 1) // page_size
        page_number = min(2, page_count)
        team_page = self.client.get(reverse('run_detail', args=[run.pk]), {'page': page_number})
        self.assertEqual(team_page.status_code, 200)
        self.assertEqual(team_page.context['team_count'], team_count)
        self.assertEqual(team_page.context['team_page'].number, page_number)
        expected_page_names = expected_team_names[(page_number - 1) * page_size:page_number * page_size]
        self.assertEqual([team.name for team in team_page.context['teams']], expected_page_names)
        self.assertContains(team_page, f'Page {page_number} of {page_count}')
        self.assertContains(team_page, f'{len(students)} of {len(students)} students allocated')
        self.assertContains(team_page, '<td>-</td>', html=True)

        export = self.client.get(reverse('export_run_csv', args=[run.pk]))
        rows = list(csv.reader(StringIO(export.content.decode('utf-8'))))
        self.assertEqual(rows[0], ['first_name', 'last_name', 'email', 'team'])
        self.assertEqual(len(rows) - 1, len(students))
        self.assertTrue(all(len(row) == 4 for row in rows))
        self.assertEqual(rows[1:], sorted(
            rows[1:],
            key=lambda row: (natural_key(row[3]), row[1].casefold(), row[0].casefold(), row[2]),
        ))
        emails = [row[2] for row in rows[1:]]
        self.assertEqual(len(set(emails)), len(students))
        self.assertEqual(set(emails), {student.email for student in students})

    def test_run_page_and_export_keep_all_persisted_teams(self):
        cohort = Cohort.objects.create(project=self.project, original_filename='cohort-10.csv')
        students = [
            Student.objects.create(
                cohort=cohort,
                first_name=f'Student {number}',
                last_name=f'{number:02}',
                email=f'small-cohort-{number}@example.org',
                c_score=None if number % 2 == 0 else number,
            )
            for number in range(10)
        ]
        run = AllocationRun.objects.create(
            project=self.project,
            cohort=cohort,
            status=AllocationRun.Status.OK,
            policy_snapshot={'team_size': {'min_size': 1, 'max_size': 5}},
        )
        sizes = [3, 3, 2, 2]
        offset = 0
        for team_number, size in enumerate(sizes, start=1):
            team = Team.objects.create(run=run, name=f'Team {team_number}')
            for student in students[offset:offset + size]:
                TeamMembership.objects.create(team=team, student=student)
            offset += size

        self.client.force_login(self.owner)
        page = self.client.get(reverse('run_detail', args=[run.pk]))
        self.assertEqual(page.context['team_count'], 4)
        self.assertEqual([team.name for team in page.context['teams']], [
            'Team 1', 'Team 2', 'Team 3', 'Team 4',
        ])
        self.assertEqual(page.context['allocated_count'], 10)

        export = self.client.get(reverse('export_run_csv', args=[run.pk]))
        rows = list(csv.reader(StringIO(export.content.decode('utf-8'))))
        self.assertEqual(rows[0], ['first_name', 'last_name', 'email', 'team'])
        self.assertEqual(len(rows) - 1, 10)
        self.assertEqual({row[2] for row in rows[1:]}, {student.email for student in students})
        self.assertEqual({row[3] for row in rows[1:]}, {'Team 1', 'Team 2', 'Team 3', 'Team 4'})
