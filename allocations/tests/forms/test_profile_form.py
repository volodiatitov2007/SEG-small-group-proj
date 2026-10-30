from django.test import TestCase

from allocations.forms import ProfileForm
from allocations.tests.helpers import PASSWORD, create_user


class ProfileFormTestCase(TestCase):
    """Tests of the form used by users to edit their own profile."""

    def setUp(self):
        self.user = create_user()
        self.data = {
            'username': 'johnny',
            'first_name': 'Johnny',
            'last_name': 'Dough',
            'email': 'johnny@example.org',
        }

    def test_form_has_the_necessary_fields(self):
        form = ProfileForm(instance=self.user)
        self.assertEqual(list(form.fields), ['username', 'first_name', 'last_name', 'email'])

    def test_form_does_not_let_users_make_themselves_superusers(self):
        form = ProfileForm(instance=self.user)
        self.assertNotIn('is_superuser', form.fields)

    def test_form_does_not_contain_password_fields(self):
        form = ProfileForm(instance=self.user)
        for field_name in form.fields:
            self.assertNotIn('password', field_name)

    def test_fields_have_bootstrap_class(self):
        form = ProfileForm(instance=self.user)
        for field in form.fields.values():
            self.assertEqual(field.widget.attrs['class'], 'form-control')

    def test_form_shows_current_details(self):
        form = ProfileForm(instance=self.user)
        self.assertEqual(form['username'].value(), 'johndoe')
        self.assertEqual(form['email'].value(), 'johndoe@example.org')

    def test_valid_form(self):
        form = ProfileForm(self.data, instance=self.user)
        self.assertTrue(form.is_valid())

    def test_form_with_unchanged_details_is_valid(self):
        data = {
            'username': 'johndoe',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'johndoe@example.org',
        }
        form = ProfileForm(data, instance=self.user)
        self.assertTrue(form.is_valid())

    def test_form_rejects_blank_fields(self):
        for field_name in self.data:
            with self.subTest(field=field_name):
                data = dict(self.data, **{field_name: ''})
                form = ProfileForm(data, instance=self.user)
                self.assertFalse(form.is_valid())
                self.assertIn(field_name, form.errors)

    def test_form_rejects_invalid_email(self):
        self.data['email'] = 'not an email'
        form = ProfileForm(self.data, instance=self.user)
        self.assertFalse(form.is_valid())

    def test_form_rejects_username_of_another_user(self):
        create_user('janedoe', 'Jane', 'Doe')
        self.data['username'] = 'janedoe'
        form = ProfileForm(self.data, instance=self.user)
        self.assertFalse(form.is_valid())

    def test_form_rejects_email_of_another_user(self):
        create_user('janedoe', 'Jane', 'Doe')
        self.data['email'] = 'janedoe@example.org'
        form = ProfileForm(self.data, instance=self.user)
        self.assertFalse(form.is_valid())

    def test_save_updates_user(self):
        form = ProfileForm(self.data, instance=self.user)
        form.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'johnny')
        self.assertEqual(self.user.first_name, 'Johnny')
        self.assertEqual(self.user.last_name, 'Dough')
        self.assertEqual(self.user.email, 'johnny@example.org')

    def test_save_does_not_change_password_or_superuser_status(self):
        form = ProfileForm(dict(self.data, is_superuser='on'), instance=self.user)
        form.save()
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))
        self.assertFalse(self.user.is_superuser)
