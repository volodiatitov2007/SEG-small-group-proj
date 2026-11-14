import json

from django.test import SimpleTestCase

from allocations.policies import RULES, Rule, TeamSizeRule, rule_from_dict


class RuleSerialisationTestCase(SimpleTestCase):
    """Rules survive a round trip through JSON, so allocation runs can snapshot them."""

    def test_team_size_rule_to_dict(self):
        rule = TeamSizeRule(4, 5, hard=False, priority=2)
        self.assertEqual(
            rule.to_dict(),
            {"key": "team_size", "hard": False, "priority": 2, "min_size": 4, "max_size": 5},
        )

    def test_round_trip_through_json_gives_equal_rule(self):
        rule = TeamSizeRule(3, 6, hard=True, priority=1)
        restored = rule_from_dict(json.loads(json.dumps(rule.to_dict())))
        self.assertEqual(restored, rule)
        self.assertIsInstance(restored, TeamSizeRule)

    def test_rules_with_different_settings_are_not_equal(self):
        self.assertNotEqual(TeamSizeRule(4, 5), TeamSizeRule(4, 6))

    def test_registry_contains_team_size(self):
        self.assertIs(RULES["team_size"], TeamSizeRule)

    def test_unknown_key_is_rejected(self):
        with self.assertRaises(KeyError):
            rule_from_dict({"key": "nonsense"})


class BaseRuleTestCase(SimpleTestCase):
    """Tests of the behaviour every rule inherits from Rule."""

    def test_base_rule_has_no_parameters(self):
        self.assertEqual(Rule(hard=True).to_dict(), {"key": "base", "hard": True, "priority": 1})

    def test_base_rule_cannot_check_teams(self):
        with self.assertRaises(NotImplementedError):
            Rule(hard=True).check_team("Team 1", [])

    def test_repr_shows_settings(self):
        self.assertIn("'min_size': 4", repr(TeamSizeRule(4, 5)))
