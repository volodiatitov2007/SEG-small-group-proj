from django import forms
from django.test import TestCase

from allocations.forms import PasswordForm
from allocations.tests.helpers import PASSWORD, create_user


class PasswordFormTestCase(TestCase):
    """Tests of the form used by users to change their own password."""

    def setUp(self):
        self.user = create_user()
        self.data = {
            'old_password': PASSWORD,
            'new_password': 'NewPassword456',
            'new_password_confirmation': 'NewPassword456',
        }

    def form_with_new_password(self, new_password):
        data = dict(self.data, new_password=new_password, new_password_confirmation=new_password)
        return PasswordForm(self.user, data)

    def test_form_has_the_necessary_fields(self):
        form = PasswordForm(self.user)
        self.assertEqual(list(form.fields), ['old_password', 'new_password', 'new_password_confirmation'])

    def test_passwords_are_hidden_while_typing(self):
        form = PasswordForm(self.user)
        for field in form.fields.values():
            self.assertIsInstance(field.widget, forms.PasswordInput)

    def test_fields_have_bootstrap_class(self):
        form = PasswordForm(self.user)
        for field in form.fields.values():
            self.assertEqual(field.widget.attrs['class'], 'form-control')

    def test_valid_form(self):
        form = PasswordForm(self.user, self.data)
        self.assertTrue(form.is_valid())

    def test_form_rejects_wrong_old_password(self):
        self.data['old_password'] = 'WrongPassword123'
        form = PasswordForm(self.user, self.data)
        self.assertFalse(form.is_valid())
        self.assertIn('old_password', form.errors)

    def test_form_rejects_blank_fields(self):
        for field_name in self.data:
            with self.subTest(field=field_name):
                data = dict(self.data, **{field_name: ''})
                form = PasswordForm(self.user, data)
                self.assertFalse(form.is_valid())

    def test_form_rejects_different_confirmation(self):
        self.data['new_password_confirmation'] = 'OtherPassword789'
        form = PasswordForm(self.user, self.data)
        self.assertFalse(form.is_valid())
        self.assertIn('new_password_confirmation', form.errors)

    def test_form_rejects_short_password(self):
        form = self.form_with_new_password('Ab1cd2e')
        self.assertFalse(form.is_valid())

    def test_form_rejects_common_password(self):
        form = self.form_with_new_password('Password123')
        self.assertFalse(form.is_valid())

    def test_form_rejects_entirely_numeric_password(self):
        form = self.form_with_new_password('8462951370')
        self.assertFalse(form.is_valid())

    def test_form_rejects_password_similar_to_username(self):
        form = self.form_with_new_password('johndoe1')
        self.assertFalse(form.is_valid())

    def test_save_changes_password(self):
        form = PasswordForm(self.user, self.data)
        form.is_valid()
        form.save()
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPassword456'))
        self.assertFalse(self.user.check_password(PASSWORD))
