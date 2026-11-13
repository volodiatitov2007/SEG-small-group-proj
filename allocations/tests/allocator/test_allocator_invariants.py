from django.test import TestCase

from allocations.allocator import INFEASIBLE, allocate
from allocations.policies import TeamSizeRule
from allocations.policies.evaluator import evaluate, is_valid
from allocations.tests.allocator.helpers import (
    FakeAttainmentSpreadRule, FakeGenderRule, assert_empty_non_ok_result, make_students,
)


class OkResultInvariantsTestCase(TestCase):
    """Tests of the invariants every status-'ok' allocation result must satisfy."""

    def setUp(self):
        self.students = make_students(
            20,
            genders=[1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2],
            c_scores=[5, 9, 2, 7, 1, 8, 3, 6, 4, 0, 5, 9, 2, 7, 1, 8, 3, 6, 4, 0],
        )
        self.rules = [TeamSizeRule(min_size=4, max_size=5), FakeGenderRule(),
                      FakeAttainmentSpreadRule(max_spread=3)]
        self.result = allocate(self.students, self.rules, seed=11)

    def test_each_student_appears_in_exactly_one_team(self):
        allocated_ids = sorted(student.id for members in self.result.teams.values()
                               for student in members)
        self.assertEqual(allocated_ids, sorted(student.id for student in self.students))

    def test_team_sizes_sum_to_the_number_of_students(self):
        self.assertEqual(sum(len(members) for members in self.result.teams.values()), 20)

    def test_every_team_size_is_within_the_minimum_and_maximum(self):
        for name, members in self.result.teams.items():
            self.assertTrue(4 <= len(members) <= 5, f'{name} has {len(members)} members.')

    def test_result_is_valid_under_every_rule(self):
        self.assertTrue(is_valid(self.rules, self.result.teams))

    def test_reported_violations_equal_a_fresh_evaluation_of_the_result(self):
        self.assertEqual(self.result.violations, evaluate(self.rules, self.result.teams))

    def test_every_reported_violation_is_soft(self):
        self.assertFalse(any(violation.hard for violation in self.result.violations))

    def test_teams_are_named_team_1_through_team_k_in_order(self):
        team_count = len(self.result.teams)
        self.assertEqual(list(self.result.teams),
                         [f'Team {number}' for number in range(1, team_count + 1)])

    def test_duration_seconds_is_non_negative_for_ok_results(self):
        self.assertGreaterEqual(self.result.duration_seconds, 0)

    def test_non_ok_result_has_empty_teams_and_violations_and_non_negative_duration(self):
        result = allocate(make_students(7), self.rules)
        self.assertEqual(result.status, INFEASIBLE)
        assert_empty_non_ok_result(self, result)
