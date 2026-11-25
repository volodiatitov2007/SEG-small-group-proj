from django.test import SimpleTestCase

from allocations.policies import GenderRule, Rule, TeamSizeRule, describe_rules


class DescribeRulesTestCase(SimpleTestCase):
    """Tests of the short descriptions of rules shown to staff."""

    def test_team_size_rule(self):
        self.assertEqual(TeamSizeRule(4, 5).describe(), 'Team size 4-5 (hard)')

    def test_soft_rule_names_its_priority(self):
        self.assertEqual(TeamSizeRule(3, 6, hard=False, priority=2).describe(), 'Team size 3-6 (soft, priority 2)')

    def test_base_rule(self):
        self.assertEqual(Rule(hard=True).describe(), 'Rule (hard)')

    def test_describe_rules_gives_one_line_per_saved_rule(self):
        saved = [TeamSizeRule(4, 5).to_dict(), GenderRule().to_dict()]
        self.assertEqual(
            describe_rules(saved), ['Team size 4-5 (hard)', 'Gender representation (soft, priority 1)'],
        )

    def test_unknown_key_is_named_not_raised(self):
        self.assertEqual(describe_rules([{'key': 'old_rule'}]), ["Unknown rule 'old_rule'"])

    def test_renamed_setting_is_named_not_raised(self):
        self.assertEqual(describe_rules([{'key': 'team_size', 'size': 4}]), ["Unknown rule 'team_size'"])

    def test_value_that_is_not_a_dict_is_named_not_raised(self):
        self.assertEqual(describe_rules(['team_size']), ["Unknown rule 'team_size'"])

    def test_no_rules_gives_no_lines(self):
        self.assertEqual(describe_rules([]), [])
