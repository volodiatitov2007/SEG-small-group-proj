from django import forms
from django.test import TestCase

from allocations.forms import UserUpdateForm
from allocations.tests.helpers import PASSWORD, create_user


class UserUpdateFormTestCase(TestCase):
    """Tests of the form used by superusers to update users."""

    def setUp(self):
        self.user = create_user()
        self.data = {
            'username': 'johnny',
            'first_name': 'Johnny',
            'last_name': 'Dough',
            'email': 'johnny@example.org',
            'is_superuser': 'on',
        }

    def test_form_has_the_necessary_fields(self):
        form = UserUpdateForm(instance=self.user)
        self.assertEqual(
            list(form.fields),
            ['username', 'first_name', 'last_name', 'email', 'is_superuser'],
        )

    def test_superuser_field_is_a_checkbox(self):
        form = UserUpdateForm(instance=self.user)
        self.assertIsInstance(form.fields['is_superuser'].widget, forms.CheckboxInput)
        self.assertEqual(form.fields['is_superuser'].widget.attrs['class'], 'form-check-input')

    def test_form_shows_current_details(self):
        form = UserUpdateForm(instance=self.user)
        self.assertEqual(form['username'].value(), 'johndoe')
        self.assertEqual(form['first_name'].value(), 'John')
        self.assertEqual(form['last_name'].value(), 'Doe')
        self.assertEqual(form['email'].value(), 'johndoe@example.org')
        self.assertFalse(form['is_superuser'].value())

    def test_valid_form(self):
        form = UserUpdateForm(self.data, instance=self.user)
        self.assertTrue(form.is_valid())

    def test_form_rejects_blank_fields(self):
        for field_name in ['username', 'first_name', 'last_name', 'email']:
            with self.subTest(field=field_name):
                data = dict(self.data, **{field_name: ''})
                form = UserUpdateForm(data, instance=self.user)
                self.assertFalse(form.is_valid())

    def test_form_rejects_username_of_another_user(self):
        create_user('janedoe', 'Jane', 'Doe')
        self.data['username'] = 'janedoe'
        form = UserUpdateForm(self.data, instance=self.user)
        self.assertFalse(form.is_valid())

    def test_form_rejects_email_of_another_user(self):
        create_user('janedoe', 'Jane', 'Doe')
        self.data['email'] = 'janedoe@example.org'
        form = UserUpdateForm(self.data, instance=self.user)
        self.assertFalse(form.is_valid())

    def test_save_updates_user(self):
        form = UserUpdateForm(self.data, instance=self.user)
        form.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'johnny')
        self.assertEqual(self.user.first_name, 'Johnny')
        self.assertEqual(self.user.last_name, 'Dough')
        self.assertEqual(self.user.email, 'johnny@example.org')
        self.assertTrue(self.user.is_superuser)

    def test_save_can_remove_superuser_status(self):
        self.user.is_superuser = True
        self.user.save()
        del self.data['is_superuser']
        form = UserUpdateForm(self.data, instance=self.user)
        form.save()
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_superuser)

    def test_save_does_not_change_password(self):
        form = UserUpdateForm(self.data, instance=self.user)
        form.save()
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))
