from django.core.exceptions import ValidationError
from django.test import TestCase

from allocations.models import Policy, Project
from allocations.policies import GenderRule, TeamSizeRule, rule_from_dict
from allocations.tests.helpers import create_user


class PolicyModelTestCase(TestCase):
    """Tests of the Policy model."""

    def setUp(self):
        self.project = Project.objects.create(name='SEG 2026', owner=create_user())
        self.rules = [TeamSizeRule(4, 5), GenderRule(priority=2)]
        self.policy = Policy.objects.create(
            project=self.project, name='Reference', rules=[rule.to_dict() for rule in self.rules],
        )

    def test_valid_policy(self):
        try:
            self.policy.full_clean()
        except ValidationError:
            self.fail('The policy should be valid.')

    def test_name_must_not_be_blank(self):
        self.policy.name = ''
        with self.assertRaises(ValidationError):
            self.policy.full_clean()

    def test_name_may_contain_100_characters(self):
        self.policy.name = 'x' * 100
        self.policy.full_clean()

    def test_name_must_not_contain_more_than_100_characters(self):
        self.policy.name = 'x' * 101
        with self.assertRaises(ValidationError):
            self.policy.full_clean()

    def test_saved_rules_load_back_as_equal_rules(self):
        saved = Policy.objects.get(pk=self.policy.pk)
        self.assertEqual([rule_from_dict(data) for data in saved.rules], self.rules)

    def test_rules_must_not_be_empty(self):
        self.policy.rules = []
        with self.assertRaises(ValidationError):
            self.policy.full_clean()

    def test_rules_default_to_an_empty_list(self):
        self.assertEqual(Policy.objects.create(project=self.project, name='Empty').rules, [])

    def test_two_policies_in_one_project_must_not_share_a_name(self):
        duplicate = Policy(project=self.project, name='Reference')
        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_policies_in_different_projects_may_share_a_name(self):
        other_project = Project.objects.create(name='Other', owner=self.project.owner)
        Policy(project=other_project, name='Reference', rules=self.policy.rules).full_clean()

    def test_policies_are_ordered_by_name(self):
        Policy.objects.create(project=self.project, name='Another')
        self.assertEqual([policy.name for policy in self.project.policies.all()], ['Another', 'Reference'])

    def test_string_is_the_name(self):
        self.assertEqual(str(self.policy), 'Reference')

    def test_deleting_the_project_deletes_its_policies(self):
        self.project.delete()
        self.assertFalse(Policy.objects.exists())
