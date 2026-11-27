from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from allocations.allocator import AllocationResult
from allocations.models import AllocationRun, Cohort, Project, Student, Team, TeamMembership
from allocations.policies import TeamSizeRule, student_view
from allocations.policies.evaluator import check_membership
from allocations.services import run_allocation
from allocations.tests.helpers import create_user


class RunAllocationTestCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name='Project', owner=create_user())
        self.cohort = Cohort.objects.create(project=self.project, original_filename='students.csv')
        self.rules = [TeamSizeRule(4, 5).to_dict()]

    def add_students(self, count, cohort=None, **fields):
        cohort = cohort or self.cohort
        return [
            Student.objects.create(
                cohort=cohort, first_name=f'First{number}', last_name=f'Last{number}',
                email=f'student{number}@example.org', **fields,
            )
            for number in range(count)
        ]

    def assert_everyone_in_exactly_one_team(self, run, students):
        teams = {
            team.name: [student_view(member.student) for member in team.members.select_related('student')]
            for team in run.teams.all()
        }
        self.assertEqual(check_membership([student_view(student) for student in students], teams), [])
        self.assertEqual(TeamMembership.objects.filter(team__run=run).count(), len(students))

    def test_good_cohort_is_saved_as_an_ok_run_with_teams_and_memberships(self):
        students = self.add_students(10)
        run = run_allocation(self.cohort, self.rules)
        self.assertEqual(run.status, AllocationRun.Status.OK)
        self.assertEqual(run.project, self.project)
        self.assertEqual(run.cohort, self.cohort)
        self.assertEqual(run.teams.count(), 2)
        self.assertIsNotNone(run.duration_seconds)
        for team in run.teams.all():
            self.assertTrue(4 <= team.members.count() <= 5)
        self.assert_everyone_in_exactly_one_team(run, students)

    def test_policy_snapshot_holds_the_rule_dicts(self):
        self.add_students(10)
        run = run_allocation(self.cohort, self.rules)
        self.assertEqual(run.policy_snapshot, {'rules': self.rules})

    def test_infeasible_team_sizes_are_saved_as_an_infeasible_run_with_no_teams(self):
        self.add_students(3)
        run = run_allocation(self.cohort, [TeamSizeRule(5, 6).to_dict()])
        self.assertEqual(run.status, AllocationRun.Status.INFEASIBLE)
        self.assertNotEqual(run.message, '')
        self.assertEqual(run.teams.count(), 0)
        self.assertEqual(TeamMembership.objects.count(), 0)

    def test_cohort_with_no_students_is_saved_with_a_clean_message_and_no_exception(self):
        run = run_allocation(self.cohort, self.rules)
        self.assertEqual(run.status, AllocationRun.Status.INFEASIBLE)
        self.assertEqual(run.message, 'There are no students to allocate.')
        self.assertEqual(run.teams.count(), 0)

    def test_unknown_rule_key_is_saved_as_a_bad_policy_run_with_the_raw_snapshot(self):
        self.add_students(10)
        rules = [{'key': 'no_such_rule', 'hard': True, 'priority': 1}]
        run = run_allocation(self.cohort, rules)
        self.assertEqual(run.status, AllocationRun.Status.BAD_POLICY)
        self.assertIn('rule that cannot be read', run.message)
        self.assertIn('no_such_rule', run.message)
        self.assertEqual(run.policy_snapshot, {'rules': rules})
        self.assertEqual(run.teams.count(), 0)

    def test_rule_with_an_extra_parameter_is_saved_as_a_bad_policy_run_with_a_message(self):
        self.add_students(10)
        rules = [{'key': 'team_size', 'hard': True, 'priority': 1, 'min_size': 4, 'max_size': 5, 'bogus': 1}]
        run = run_allocation(self.cohort, rules)
        self.assertEqual(run.status, AllocationRun.Status.BAD_POLICY)
        self.assertIn('rule that cannot be read', run.message)
        self.assertIn('bogus', run.message)
        self.assertEqual(run.policy_snapshot, {'rules': rules})
        self.assertEqual(run.teams.count(), 0)

    def test_rule_that_is_not_a_dict_is_saved_as_a_bad_policy_run_not_an_error(self):
        self.add_students(10)
        for rules in (['team_size'], [None]):
            run = run_allocation(self.cohort, rules)
            self.assertEqual(run.status, AllocationRun.Status.BAD_POLICY)
            self.assertIn('rule that cannot be read', run.message)
            self.assertEqual(run.policy_snapshot, {'rules': rules})
            self.assertEqual(run.teams.count(), 0)

    def test_policy_whose_rules_are_not_a_list_is_saved_as_a_bad_policy_run(self):
        self.add_students(10)
        run = run_allocation(self.cohort, SimpleNamespace(rules=None))
        self.assertEqual(run.status, AllocationRun.Status.BAD_POLICY)
        self.assertEqual(run.teams.count(), 0)

    def test_policy_object_with_a_rules_attribute_is_accepted(self):
        students = self.add_students(10)
        run = run_allocation(self.cohort, SimpleNamespace(rules=self.rules))
        self.assertEqual(run.status, AllocationRun.Status.OK)
        self.assertEqual(run.policy_snapshot, {'rules': self.rules})
        self.assert_everyone_in_exactly_one_team(run, students)

    def test_running_again_on_the_same_cohort_makes_a_second_run_and_keeps_the_first_runs_teams(self):
        self.add_students(10)
        first = run_allocation(self.cohort, self.rules)
        first_teams = list(first.teams.values_list('pk', 'name'))
        first_memberships = TeamMembership.objects.filter(team__run=first).count()
        second = run_allocation(self.cohort, self.rules)
        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(AllocationRun.objects.count(), 2)
        self.assertEqual(list(first.teams.values_list('pk', 'name')), first_teams)
        self.assertEqual(TeamMembership.objects.filter(team__run=first).count(), first_memberships)
        self.assertEqual(Team.objects.filter(run=second).count(), 2)

    def test_timeout_is_saved_with_the_allocator_message_that_is_not_proof_of_impossibility(self):
        self.add_students(10)
        message = ('No allocation meeting every hard rule was found in time. '
                   'This is not proof that none exists.')
        timed_out = AllocationResult(status='timeout', message=message, duration_seconds=0.5)
        with patch('allocations.services.allocate', return_value=timed_out):
            run = run_allocation(self.cohort, self.rules)
        self.assertEqual(run.status, AllocationRun.Status.TIMEOUT)
        self.assertIn('found in time', run.message)
        self.assertIn('not proof', run.message)
        self.assertEqual(run.duration_seconds, 0.5)
        self.assertEqual(run.teams.count(), 0)

    def test_students_with_missing_c_score_and_not_provided_gender_and_ethnicity_are_all_allocated(self):
        students = self.add_students(4, c_score=None, gender=0, ethnicity=0)
        students += [
            Student.objects.create(
                cohort=self.cohort, first_name='Scored', last_name=f'Student{number}',
                email=f'scored{number}@example.org', c_score=40 + number, gender=1 + number % 3, ethnicity=2,
            )
            for number in range(6)
        ]
        run = run_allocation(self.cohort, self.rules)
        self.assertEqual(run.status, AllocationRun.Status.OK)
        self.assert_everyone_in_exactly_one_team(run, students)

    def test_violations_are_saved_as_dicts_whose_team_matches_a_saved_team_name(self):
        self.add_students(10)
        rules = [TeamSizeRule(3, 5).to_dict(), TeamSizeRule(3, 3, hard=False, priority=2).to_dict()]
        run = run_allocation(self.cohort, rules)
        self.assertEqual(run.status, AllocationRun.Status.OK)
        self.assertTrue(run.violations)
        team_names = set(run.teams.values_list('name', flat=True))
        for violation in run.violations:
            self.assertIsInstance(violation, dict)
            self.assertIn(violation['team'], team_names)
            self.assertFalse(violation['hard'])

    def test_only_the_given_cohorts_students_are_allocated(self):
        students = self.add_students(10)
        other = Cohort.objects.create(project=self.project, original_filename='other.csv')
        Student.objects.create(cohort=other, first_name='Other', last_name='Cohort', email='other@example.org')
        run = run_allocation(self.cohort, self.rules)
        self.assert_everyone_in_exactly_one_team(run, students)
