from django import forms
from django.test import RequestFactory, TestCase

from allocations.forms import LogInForm
from allocations.tests.helpers import PASSWORD, create_user


class LogInFormTestCase(TestCase):
    """Tests of the form used to log in."""

    def setUp(self):
        self.user = create_user()
        self.request = RequestFactory().get('/')
        self.data = {'username': 'johndoe', 'password': PASSWORD}

    def test_form_has_the_necessary_fields(self):
        form = LogInForm(self.request)
        self.assertEqual(list(form.fields), ['username', 'password'])

    def test_password_is_hidden_while_typing(self):
        form = LogInForm(self.request)
        self.assertIsInstance(form.fields['password'].widget, forms.PasswordInput)

    def test_fields_have_bootstrap_class(self):
        form = LogInForm(self.request)
        for field in form.fields.values():
            self.assertEqual(field.widget.attrs['class'], 'form-control')

    def test_form_accepts_the_right_username_and_password(self):
        form = LogInForm(self.request, data=self.data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.get_user(), self.user)

    def test_form_rejects_a_wrong_password(self):
        self.data['password'] = 'WrongPassword123'
        form = LogInForm(self.request, data=self.data)
        self.assertFalse(form.is_valid())

    def test_form_rejects_an_unknown_username(self):
        self.data['username'] = 'nobody'
        form = LogInForm(self.request, data=self.data)
        self.assertFalse(form.is_valid())

    def test_form_rejects_a_blank_username(self):
        self.data['username'] = ''
        form = LogInForm(self.request, data=self.data)
        self.assertFalse(form.is_valid())

    def test_form_rejects_a_blank_password(self):
        self.data['password'] = ''
        form = LogInForm(self.request, data=self.data)
        self.assertFalse(form.is_valid())

    def test_form_rejects_an_inactive_user(self):
        self.user.is_active = False
        self.user.save()
        form = LogInForm(self.request, data=self.data)
        self.assertFalse(form.is_valid())
