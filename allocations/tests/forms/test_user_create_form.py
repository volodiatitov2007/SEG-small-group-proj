from django import forms
from django.test import TestCase

from allocations.forms import UserCreateForm
from allocations.models import User
from allocations.tests.helpers import create_user


class UserCreateFormTestCase(TestCase):
    """Tests of the form used by superusers to create users."""

    def setUp(self):
        self.data = {
            'username': 'alicechen',
            'first_name': 'Alice',
            'last_name': 'Chen',
            'email': 'alicechen@example.org',
            'password': 'Allocation123',
            'password_confirmation': 'Allocation123',
        }

    def test_form_has_the_necessary_fields(self):
        form = UserCreateForm()
        self.assertEqual(
            list(form.fields),
            ['username', 'first_name', 'last_name', 'email', 'is_superuser', 'password', 'password_confirmation'],
        )

    def test_passwords_are_hidden_while_typing(self):
        form = UserCreateForm()
        self.assertIsInstance(form.fields['password'].widget, forms.PasswordInput)
        self.assertIsInstance(form.fields['password_confirmation'].widget, forms.PasswordInput)

    def test_superuser_field_is_a_checkbox(self):
        form = UserCreateForm()
        self.assertIsInstance(form.fields['is_superuser'].widget, forms.CheckboxInput)
        self.assertEqual(form.fields['is_superuser'].widget.attrs['class'], 'form-check-input')

    def test_other_fields_have_bootstrap_class(self):
        form = UserCreateForm()
        for field_name, field in form.fields.items():
            if field_name != 'is_superuser':
                self.assertEqual(field.widget.attrs['class'], 'form-control')

    def test_valid_form(self):
        form = UserCreateForm(self.data)
        self.assertTrue(form.is_valid())

    def test_superuser_field_is_optional(self):
        form = UserCreateForm(self.data)
        self.assertTrue(form.is_valid())
        self.assertFalse(form.cleaned_data['is_superuser'])

    def test_form_rejects_blank_fields(self):
        for field_name in self.data:
            with self.subTest(field=field_name):
                data = dict(self.data, **{field_name: ''})
                form = UserCreateForm(data)
                self.assertFalse(form.is_valid())

    def test_form_rejects_invalid_username(self):
        self.data['username'] = 'alice chen'
        form = UserCreateForm(self.data)
        self.assertFalse(form.is_valid())

    def test_form_rejects_invalid_email(self):
        self.data['email'] = 'not an email'
        form = UserCreateForm(self.data)
        self.assertFalse(form.is_valid())

    def test_form_rejects_existing_username(self):
        create_user('alicechen', 'Alice', 'Chen')
        self.data['email'] = 'alice@example.org'
        form = UserCreateForm(self.data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_form_rejects_existing_username_in_different_case(self):
        create_user('alicechen', 'Alice', 'Chen')
        self.data['username'] = 'AliceChen'
        self.data['email'] = 'alice@example.org'
        form = UserCreateForm(self.data)
        self.assertFalse(form.is_valid())

    def test_form_rejects_existing_email(self):
        create_user('alice', 'Alice', 'Chen')
        self.data['email'] = 'alice@example.org'
        form = UserCreateForm(self.data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_form_rejects_different_password_confirmation(self):
        self.data['password_confirmation'] = 'OtherPassword456'
        form = UserCreateForm(self.data)
        self.assertFalse(form.is_valid())

    def test_form_rejects_weak_passwords(self):
        for password in ['Ab1cd2e', 'Password123', '8462951370', 'alicechen1']:
            with self.subTest(password=password):
                data = dict(self.data, password=password, password_confirmation=password)
                form = UserCreateForm(data)
                self.assertFalse(form.is_valid())

    def test_save_creates_user(self):
        form = UserCreateForm(self.data)
        form.save()
        user = User.objects.get(username='alicechen')
        self.assertEqual(user.first_name, 'Alice')
        self.assertEqual(user.last_name, 'Chen')
        self.assertEqual(user.email, 'alicechen@example.org')
        self.assertFalse(user.is_superuser)

    def test_save_stores_password_securely(self):
        form = UserCreateForm(self.data)
        user = form.save()
        self.assertNotEqual(user.password, 'Allocation123')
        self.assertTrue(user.check_password('Allocation123'))

    def test_save_can_create_superuser(self):
        self.data['is_superuser'] = 'on'
        form = UserCreateForm(self.data)
        user = form.save()
        self.assertTrue(user.is_superuser)
