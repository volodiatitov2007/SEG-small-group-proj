import random

from django.test import SimpleTestCase

from allocations.policies import TeamSizeRule
from allocations.policies.evaluator import WEIGHT, evaluate, is_valid, soft_cost
from allocations.tests.policies.helpers import make_teams


class EvaluateTestCase(SimpleTestCase):
    """Tests of evaluate()."""

    def test_valid_allocation_has_no_violations(self):
        rules = [TeamSizeRule(4, 5)]
        self.assertEqual(evaluate(rules, make_teams(4, 5, 5)), [])

    def test_reports_every_offending_team(self):
        rules = [TeamSizeRule(4, 5)]
        violations = evaluate(rules, make_teams(3, 5, 6))
        self.assertEqual([v.team for v in violations], ["Team 1", "Team 3"])

    def test_no_rules_means_no_violations(self):
        self.assertEqual(evaluate([], make_teams(1, 9)), [])

    def test_hard_violations_come_first_then_priority(self):
        rules = [
            TeamSizeRule(4, 4, hard=False, priority=3),
            TeamSizeRule(4, 4, hard=False, priority=1),
            TeamSizeRule(4, 4, hard=True, priority=2),
        ]
        violations = evaluate(rules, make_teams(5))
        self.assertEqual(
            [(v.hard, v.priority) for v in violations],
            [(True, 2), (False, 1), (False, 3)],
        )

    def test_reported_violations_match_a_hand_check_on_random_allocations(self):
        generator = random.Random(2026)
        rule = TeamSizeRule(4, 5)
        for _ in range(200):
            sizes = [generator.randint(0, 8) for _ in range(generator.randint(1, 10))]
            teams = make_teams(*sizes)
            reported = {v.team for v in evaluate([rule], teams)}
            expected = {name for name, members in teams.items() if not 4 <= len(members) <= 5}
            with self.subTest(sizes=sizes):
                self.assertEqual(reported, expected)


class IsValidTestCase(SimpleTestCase):
    """Tests of is_valid()."""

    def test_valid_when_no_hard_violation(self):
        self.assertTrue(is_valid([TeamSizeRule(4, 5)], make_teams(4, 5)))

    def test_invalid_when_hard_violation(self):
        self.assertFalse(is_valid([TeamSizeRule(4, 5)], make_teams(4, 3)))

    def test_soft_violations_do_not_make_allocation_invalid(self):
        self.assertTrue(is_valid([TeamSizeRule(4, 5, hard=False)], make_teams(3)))


class SoftCostTestCase(SimpleTestCase):
    """Tests of soft_cost()."""

    def test_zero_when_no_soft_violations(self):
        self.assertEqual(soft_cost([TeamSizeRule(4, 5, hard=False)], make_teams(4, 5)), 0)

    def test_hard_violations_are_not_counted(self):
        self.assertEqual(soft_cost([TeamSizeRule(4, 5)], make_teams(1)), 0)

    def test_weighted_by_priority_and_amount(self):
        rule = TeamSizeRule(4, 5, hard=False, priority=2)
        self.assertEqual(soft_cost([rule], make_teams(2)), 2 * WEIGHT[2])

    def test_one_high_priority_violation_outweighs_five_low_ones(self):
        high = [TeamSizeRule(4, 5, hard=False, priority=1)]
        low = [TeamSizeRule(4, 5, hard=False, priority=3)]
        self.assertGreater(
            soft_cost(high, make_teams(3)),
            soft_cost(low, make_teams(3, 3, 3, 3, 3)),
        )
