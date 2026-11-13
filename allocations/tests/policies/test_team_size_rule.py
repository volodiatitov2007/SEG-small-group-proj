from django.test import SimpleTestCase

from allocations.policies import TeamSizeRule
from allocations.tests.policies.helpers import make_students


class TeamSizeRuleTestCase(SimpleTestCase):
    """Tests of TeamSizeRule on single teams."""

    def setUp(self):
        self.rule = TeamSizeRule(min_size=4, max_size=5)

    def check(self, size):
        return self.rule.check_team("Team 1", make_students(size))

    def test_team_of_minimum_size_passes(self):
        self.assertEqual(self.check(4), [])

    def test_team_of_maximum_size_passes(self):
        self.assertEqual(self.check(5), [])

    def test_team_one_below_minimum_fails(self):
        [violation] = self.check(3)
        self.assertEqual(violation.message, "Team 1 has 3 students; the minimum is 4.")
        self.assertEqual(violation.amount, 1)

    def test_team_one_above_maximum_fails(self):
        [violation] = self.check(6)
        self.assertEqual(violation.message, "Team 1 has 6 students; the maximum is 5.")
        self.assertEqual(violation.amount, 1)

    def test_amount_grows_with_distance_from_limit(self):
        [violation] = self.check(1)
        self.assertEqual(violation.amount, 3)
        self.assertEqual(violation.message, "Team 1 has 1 student; the minimum is 4.")

    def test_empty_team_fails(self):
        [violation] = self.check(0)
        self.assertEqual(violation.amount, 4)

    def test_violation_carries_rule_settings(self):
        rule = TeamSizeRule(4, 5, hard=False, priority=2)
        [violation] = rule.check_team("Team 3", make_students(2))
        self.assertEqual(violation.rule, "team_size")
        self.assertFalse(violation.hard)
        self.assertEqual(violation.priority, 2)
        self.assertEqual(violation.team, "Team 3")

    def test_is_hard_by_default(self):
        self.assertTrue(self.rule.hard)

    def test_minimum_equal_to_maximum_is_allowed(self):
        rule = TeamSizeRule(4, 4)
        self.assertEqual(rule.check_team("Team 1", make_students(4)), [])

    def test_minimum_below_one_is_rejected(self):
        with self.assertRaises(ValueError):
            TeamSizeRule(0, 5)

    def test_minimum_above_maximum_is_rejected(self):
        with self.assertRaises(ValueError):
            TeamSizeRule(6, 5)

    def test_unknown_priority_is_rejected(self):
        with self.assertRaises(ValueError):
            TeamSizeRule(4, 5, priority=4)

    def test_limits_are_readable_attributes(self):
        self.assertEqual(self.rule.min_size, 4)
        self.assertEqual(self.rule.max_size, 5)

    def test_check_team_needs_only_the_team_it_is_given(self):
        small, full = make_students(3), make_students(5, start=4)
        [violation] = self.rule.check_team("Team 1", small)
        self.assertEqual(violation.team, "Team 1")
        self.assertEqual(self.rule.check_team("Team 2", full), [])

    def test_check_team_gives_the_same_result_as_check_allocation(self):
        teams = {"Team 1": make_students(3), "Team 2": make_students(6, start=4)}
        one_by_one = [v for name, members in teams.items()
                      for v in self.rule.check_team(name, members)]
        self.assertEqual(one_by_one, self.rule.check_allocation(teams))

    def test_prepare_does_not_change_results(self):
        before = self.check(3)
        self.rule.prepare(make_students(300))
        self.assertEqual(self.check(3), before)
