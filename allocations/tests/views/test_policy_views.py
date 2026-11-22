from django.test import TestCase
from django.urls import reverse

from allocations.models import Policy, Project
from allocations.policies import GenderRule, TeamSizeRule
from allocations.tests.helpers import PASSWORD, create_user, log_in_url_for, messages_in


class PolicyViewsTestCase(TestCase):
    """Tests of the policy list, create and edit pages."""

    def setUp(self):
        self.owner = create_user()
        self.other_user = create_user(username='other')
        self.project = Project.objects.create(name='SEG 2026', owner=self.owner)
        self.policy = Policy.objects.create(
            project=self.project, name='Reference',
            rules=[TeamSizeRule(4, 5).to_dict(), GenderRule().to_dict()],
        )
        self.list_url = reverse('policy_list', kwargs={'project_id': self.project.id})
        self.create_url = reverse('policy_create', kwargs={'project_id': self.project.id})
        self.edit_url = reverse('policy_update', kwargs={'policy_id': self.policy.id})
        self.data = {'name': 'Small teams', 'min_size': 3, 'max_size': 4, 'use_gender_rule': 'on', 'gender_priority': 2}

    def log_in(self, user):
        self.client.login(username=user.username, password=PASSWORD)

    def test_urls(self):
        self.assertEqual(self.list_url, f'/projects/{self.project.id}/policies/')
        self.assertEqual(self.create_url, f'/projects/{self.project.id}/policies/new/')
        self.assertEqual(self.edit_url, f'/policies/{self.policy.id}/edit/')

    def test_every_page_needs_a_log_in(self):
        for url in (self.list_url, self.create_url, self.edit_url):
            with self.subTest(url=url):
                self.assertRedirects(self.client.get(url), log_in_url_for(url))

    def test_list_shows_each_policy_with_its_rules(self):
        self.log_in(self.owner)
        response = self.client.get(self.list_url)
        self.assertTemplateUsed(response, 'policy_list.html')
        self.assertContains(response, 'Reference')
        self.assertContains(response, 'Team size 4-5 (hard)')
        self.assertContains(response, 'Gender representation (soft, priority 1)')
        self.assertContains(response, self.edit_url)

    def test_list_names_a_saved_rule_the_app_no_longer_knows(self):
        self.policy.rules = [{'key': 'old_rule'}]
        self.policy.save()
        self.log_in(self.owner)
        self.assertContains(self.client.get(self.list_url), 'Unknown rule &#x27;old_rule&#x27;')

    def test_list_without_policies_says_so(self):
        self.policy.delete()
        self.log_in(self.owner)
        self.assertContains(self.client.get(self.list_url), 'No policies yet.')

    def test_list_shows_only_this_project_policies(self):
        other_project = Project.objects.create(name='Other', owner=self.owner)
        Policy.objects.create(project=other_project, name='Elsewhere')
        self.log_in(self.owner)
        self.assertNotContains(self.client.get(self.list_url), 'Elsewhere')

    def test_other_users_cannot_see_or_change_the_policies(self):
        self.log_in(self.other_user)
        for url in (self.list_url, self.create_url, self.edit_url):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(self.edit_url, self.data).status_code, 404)
        self.policy.refresh_from_db()
        self.assertEqual(self.policy.name, 'Reference')

    def test_create_page_shows_an_empty_form(self):
        self.log_in(self.owner)
        response = self.client.get(self.create_url)
        self.assertTemplateUsed(response, 'policy_form.html')
        self.assertIsNone(response.context['form'].policy)

    def test_create_saves_the_policy_and_goes_to_the_list(self):
        self.log_in(self.owner)
        response = self.client.post(self.create_url, self.data, follow=True)
        self.assertRedirects(response, self.list_url)
        policy = Policy.objects.get(name='Small teams')
        self.assertEqual(policy.project, self.project)
        self.assertEqual(policy.rules, [TeamSizeRule(3, 4).to_dict(), GenderRule(priority=2).to_dict()])
        self.assertIn('Policy Small teams has been saved.', messages_in(response))

    def test_invalid_create_shows_the_errors_and_saves_nothing(self):
        self.log_in(self.owner)
        response = self.client.post(self.create_url, {**self.data, 'min_size': 5, 'max_size': 4})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The largest team size must be at least the smallest.')
        self.assertFalse(Policy.objects.filter(name='Small teams').exists())

    def test_edit_page_starts_with_the_saved_rules(self):
        self.log_in(self.owner)
        response = self.client.get(self.edit_url)
        self.assertEqual(response.context['form'].initial['min_size'], 4)
        self.assertContains(response, 'Edit policy Reference')

    def test_edit_saves_the_changes_and_goes_to_the_list(self):
        self.log_in(self.owner)
        response = self.client.post(self.edit_url, {**self.data, 'use_gender_rule': ''}, follow=True)
        self.assertRedirects(response, self.list_url)
        self.policy.refresh_from_db()
        self.assertEqual(self.policy.name, 'Small teams')
        self.assertEqual(self.policy.rules, [TeamSizeRule(3, 4).to_dict()])

    def test_invalid_edit_keeps_the_saved_policy(self):
        self.log_in(self.owner)
        response = self.client.post(self.edit_url, {**self.data, 'name': ''})
        self.assertEqual(response.status_code, 200)
        self.policy.refresh_from_db()
        self.assertEqual(self.policy.name, 'Reference')

    def test_editing_a_policy_with_an_unknown_rule_warns_instead_of_failing(self):
        self.policy.rules = [TeamSizeRule(4, 5).to_dict(), {'key': 'old_rule'}]
        self.policy.save()
        self.log_in(self.owner)
        response = self.client.get(self.edit_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "This policy has rules the app no longer knows ('old_rule'). "
            'Saving the form replaces them with the rules chosen below.',
            messages_in(response),
        )

    def test_project_page_links_to_its_policies(self):
        self.log_in(self.owner)
        response = self.client.get(reverse('project_detail', kwargs={'project_id': self.project.id}))
        self.assertContains(response, self.list_url)
