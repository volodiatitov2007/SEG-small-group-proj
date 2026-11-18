from django.test import SimpleTestCase

from allocations.policies.evaluator import MEMBERSHIP_KEY, check_membership
from allocations.tests.policies.helpers import make_students, make_teams


class CheckMembershipTestCase(SimpleTestCase):
    """Every student of the cohort must be in exactly one team."""

    def setUp(self):
        self.teams = make_teams(4, 5)
        self.students = [member for members in self.teams.values() for member in members]

    def messages(self, students, teams):
        return [violation.message for violation in check_membership(students, teams)]

    def test_complete_allocation_has_no_problems(self):
        self.assertEqual(check_membership(self.students, self.teams), [])

    def test_empty_cohort_and_no_teams_has_no_problems(self):
        self.assertEqual(check_membership([], {}), [])

    def test_student_left_out_is_reported(self):
        [extra] = make_students(1, start=100)
        self.assertEqual(
            self.messages(self.students + [extra], self.teams),
            ['Student 100 is not in any team.'],
        )

    def test_every_student_is_reported_when_there_are_no_teams(self):
        self.assertEqual(len(check_membership(self.students, {})), len(self.students))

    def test_student_in_two_teams_is_reported(self):
        duplicate = self.teams['Team 1'][0]
        self.teams['Team 2'].append(duplicate)
        self.assertEqual(
            self.messages(self.students, self.teams),
            ['Student 1 is in more than one team (Team 1, Team 2).'],
        )

    def test_student_twice_in_the_same_team_is_reported(self):
        self.teams['Team 1'].append(self.teams['Team 1'][0])
        self.assertEqual(
            self.messages(self.students, self.teams),
            ['Student 1 is in more than one team (Team 1, Team 1).'],
        )

    def test_member_from_outside_the_cohort_is_reported(self):
        [outsider] = make_students(1, start=100)
        self.teams['Team 2'].append(outsider)
        self.assertEqual(
            self.messages(self.students, self.teams),
            ['Team 2 contains Student 100, who is not in the cohort.'],
        )

    def test_problems_are_hard_membership_violations(self):
        [violation] = check_membership(self.students[:-1], self.teams)
        self.assertEqual(violation.rule, MEMBERSHIP_KEY)
        self.assertTrue(violation.hard)
        self.assertEqual(violation.team, 'Team 2')

    def test_no_problems_exactly_when_ids_match_once(self):
        for missing in range(len(self.students)):
            cohort = self.students[:missing] + self.students[missing + 1:]
            with self.subTest(missing=missing):
                self.assertEqual(len(check_membership(cohort, self.teams)), 1)
