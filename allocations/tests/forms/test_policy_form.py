from django.test import TestCase

from allocations.forms import PolicyForm
from allocations.models import Policy, Project
from allocations.policies import GenderRule, TeamSizeRule
from allocations.tests.helpers import create_user


class PolicyFormTestCase(TestCase):
    """Tests of the form that creates and edits policies."""

    def setUp(self):
        self.project = Project.objects.create(name='SEG 2026', owner=create_user())
        self.data = {
            'name': 'Reference', 'min_size': 4, 'max_size': 5,
            'use_gender_rule': True, 'gender_priority': 2,
        }

    def form(self, policy=None, **changes):
        return PolicyForm({**self.data, **changes}, project=self.project, policy=policy)

    def test_valid_form(self):
        self.assertTrue(self.form().is_valid())

    def test_builds_team_size_and_gender_rules(self):
        form = self.form()
        form.is_valid()
        self.assertEqual(form.build_rules(), [TeamSizeRule(4, 5), GenderRule(priority=2)])

    def test_unticked_gender_rule_gives_only_team_size(self):
        form = self.form(use_gender_rule='')
        form.is_valid()
        self.assertEqual(form.build_rules(), [TeamSizeRule(4, 5)])

    def test_save_creates_a_policy_with_saved_rules(self):
        form = self.form()
        form.is_valid()
        policy = form.save()
        self.assertEqual(policy.project, self.project)
        self.assertEqual(policy.name, 'Reference')
        self.assertEqual(policy.rules, [TeamSizeRule(4, 5).to_dict(), GenderRule(priority=2).to_dict()])

    def test_minimum_equal_to_maximum_is_allowed(self):
        self.assertTrue(self.form(min_size=4, max_size=4).is_valid())

    def test_maximum_smaller_than_minimum_is_rejected(self):
        form = self.form(min_size=5, max_size=4)
        self.assertFalse(form.is_valid())
        self.assertIn('The largest team size must be at least the smallest.', form.errors['max_size'])

    def test_minimum_below_one_is_rejected(self):
        self.assertIn('min_size', self.form(min_size=0).errors)

    def test_missing_team_size_is_rejected(self):
        self.assertIn('max_size', self.form(max_size='').errors)

    def test_name_must_not_be_blank(self):
        self.assertIn('name', self.form(name='').errors)

    def test_unknown_priority_is_rejected(self):
        self.assertIn('gender_priority', self.form(gender_priority=4).errors)

    def test_name_already_used_in_the_project_is_rejected_whatever_the_case(self):
        Policy.objects.create(project=self.project, name='Reference')
        form = self.form(name='reference')
        self.assertIn('This project already has a policy with this name.', form.errors['name'])

    def test_name_used_in_another_project_is_allowed(self):
        other_project = Project.objects.create(name='Other', owner=self.project.owner)
        Policy.objects.create(project=other_project, name='Reference')
        self.assertTrue(self.form().is_valid())


class PolicyFormEditTestCase(TestCase):
    """Tests of the form when it edits a saved policy."""

    def setUp(self):
        self.project = Project.objects.create(name='SEG 2026', owner=create_user())
        self.policy = Policy.objects.create(
            project=self.project, name='Reference',
            rules=[TeamSizeRule(3, 6).to_dict(), GenderRule(priority=3).to_dict()],
        )

    def test_fields_start_with_the_saved_rules(self):
        form = PolicyForm(project=self.project, policy=self.policy)
        self.assertEqual(form.initial, {
            'name': 'Reference', 'min_size': 3, 'max_size': 6, 'use_gender_rule': True, 'gender_priority': 3,
        })

    def test_gender_rule_starts_unticked_when_the_policy_has_none(self):
        self.policy.rules = [TeamSizeRule(4, 5).to_dict()]
        form = PolicyForm(project=self.project, policy=self.policy)
        self.assertFalse(form.initial['use_gender_rule'])

    def test_unknown_saved_rule_is_listed_not_raised(self):
        self.policy.rules = [TeamSizeRule(4, 5).to_dict(), {'key': 'old_rule'}]
        form = PolicyForm(project=self.project, policy=self.policy)
        self.assertEqual(form.unreadable_rules, ['old_rule'])
        self.assertEqual(form.initial['min_size'], 4)

    def test_keeping_its_own_name_is_allowed(self):
        data = {'name': 'Reference', 'min_size': 4, 'max_size': 5, 'gender_priority': 1}
        self.assertTrue(PolicyForm(data, project=self.project, policy=self.policy).is_valid())

    def test_save_updates_the_policy_without_creating_another(self):
        data = {'name': 'Renamed', 'min_size': 4, 'max_size': 5, 'gender_priority': 1}
        form = PolicyForm(data, project=self.project, policy=self.policy)
        form.is_valid()
        form.save()
        self.policy.refresh_from_db()
        self.assertEqual(self.policy.name, 'Renamed')
        self.assertEqual(self.policy.rules, [TeamSizeRule(4, 5).to_dict()])
        self.assertEqual(Policy.objects.count(), 1)
