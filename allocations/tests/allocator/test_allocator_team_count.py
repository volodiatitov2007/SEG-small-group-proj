from unittest.mock import patch

from django.test import TestCase

from allocations import allocator
from allocations.allocator import INFEASIBLE, allocate
from allocations.policies import TeamSizeRule
from allocations.tests.allocator.helpers import assert_empty_non_ok_result, assert_ok_invariants, make_students


class TeamCountSearchTestCase(TestCase):
    """Tests that every team count the size range allows is tried, fewest teams first."""

    def setUp(self):
        self.students = make_students(10)
        self.hard_rule = TeamSizeRule(3, 5)
        self.soft_rule = TeamSizeRule(3, 3, hard=False, priority=2)

    def counts_tried(self, rules, students=None):
        with patch.object(allocator, '_greedy_start', wraps=allocator._greedy_start) as greedy_start:
            result = allocate(students or self.students, rules, seed=1)
        return [call.args[1] for call in greedy_start.call_args_list], result

    def test_ten_students_in_teams_of_three_to_five_try_two_and_three_teams_only(self):
        counts, result = self.counts_tried([self.hard_rule, self.soft_rule])
        self.assertEqual(counts, [2, 3])
        for members in result.teams.values():
            self.assertTrue(3 <= len(members) <= 5)

    def test_soft_size_rule_makes_the_search_prefer_three_teams_over_two(self):
        result = allocate(self.students, [self.hard_rule, self.soft_rule])
        assert_ok_invariants(self, result, self.students, [self.hard_rule, self.soft_rule])
        self.assertEqual(len(result.teams), 3)
        self.assertEqual(sorted(len(members) for members in result.teams.values()), [3, 3, 4])

    def test_equal_scores_give_the_smaller_team_count(self):
        result = allocate(self.students, [self.hard_rule])
        assert_ok_invariants(self, result, self.students, [self.hard_rule])
        self.assertEqual(len(result.teams), 2)

    def test_perfect_score_stops_the_search_at_the_first_count(self):
        counts, _ = self.counts_tried([self.hard_rule])
        self.assertEqual(counts, [2])

    def test_same_seed_and_max_steps_give_identical_teams(self):
        rules = [self.hard_rule, self.soft_rule]
        first = allocate(self.students, rules, seed=7, max_steps=200)
        second = allocate(self.students, rules, seed=7, max_steps=200)
        self.assertEqual(first.teams, second.teams)
        self.assertEqual(first.violations, second.violations)

    def test_infeasible_range_is_infeasible_and_tries_no_count(self):
        counts, result = self.counts_tried([TeamSizeRule(5, 6)], make_students(3))
        self.assertEqual(result.status, INFEASIBLE)
        self.assertEqual(counts, [])
        assert_empty_non_ok_result(self, result)
        self.assertNotEqual(result.message, '')

    def test_soft_size_rule_with_an_infeasible_range_uses_the_count_that_breaks_it_least(self):
        counts, result = self.counts_tried([TeamSizeRule(5, 6, hard=False)], make_students(3))
        self.assertEqual(counts, [1])
        self.assertEqual(result.status, 'ok')
        self.assertEqual(len(result.teams), 1)

    def test_team_counts_lists_every_fitting_count_fewest_first(self):
        self.assertEqual(list(allocator._team_counts(10, 3, 5)), [2, 3])
        self.assertEqual(list(allocator._team_counts(12, 4, 4)), [3])

    def test_three_hundred_students_in_teams_of_four_to_five_finish_well_under_thirty_seconds(self):
        students = make_students(300, c_scores=[number % 101 for number in range(300)])
        rules = [TeamSizeRule(4, 5)]
        result = allocate(students, rules)
        assert_ok_invariants(self, result, students, rules)
        self.assertLess(result.duration_seconds, 30)
