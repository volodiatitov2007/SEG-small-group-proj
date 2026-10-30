from django.test import TestCase
from django.urls import reverse

from allocations.tests.helpers import create_user


class FormPartialTestCase(TestCase):
    """Tests of partials/form.html, which shows the fields of a form."""

    def setUp(self):
        self.user = create_user()
        self.client.force_login(self.user)

    def test_partial_is_used_by_forms(self):
        response = self.client.get(reverse('profile'))
        self.assertTemplateUsed(response, 'partials/form.html')

    def test_partial_shows_label_and_input_of_each_field(self):
        response = self.client.get(reverse('profile'))
        for field_name in ['username', 'first_name', 'last_name', 'email']:
            self.assertContains(response, f'<label for="id_{field_name}">')
            self.assertContains(response, f'name="{field_name}"')

    def test_partial_shows_help_text(self):
        response = self.client.get(reverse('password'))
        self.assertContains(response, '<div class="form-text">')

    def test_partial_shows_field_errors(self):
        data = {'username': '', 'first_name': 'John', 'last_name': 'Doe', 'email': 'johndoe@example.org'}
        response = self.client.post(reverse('profile'), data)
        self.assertContains(response, '<div class="text-danger">This field is required.</div>')
