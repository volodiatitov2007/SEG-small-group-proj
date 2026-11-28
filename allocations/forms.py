from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    SetPasswordMixin,
    UserCreationForm,
)

from .models import Project, User
from .policies import GenderRule, TeamSizeRule, rule_from_dict


class BootstrapFormMixin:
    """Add Bootstrap's CSS classes to the input widgets of a form."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'


PRIORITY_CHOICES = [(1, '1 (high)'), (2, '2 (medium)'), (3, '3 (low)')]


class PolicyForm(BootstrapFormMixin, forms.Form):
    """Form to create or edit a policy: a team size rule, plus an optional gender rule."""

    name = forms.CharField(max_length=100)
    min_size = forms.IntegerField(label='Smallest team size', min_value=1, initial=4)
    max_size = forms.IntegerField(label='Largest team size', min_value=1, initial=5)
    use_gender_rule = forms.BooleanField(
        label='Use the gender representation rule',
        required=False,
        initial=True,
        help_text='Avoid a student being the only one of their disclosed gender in a team.',
    )
    gender_priority = forms.TypedChoiceField(
        label='Gender rule priority', choices=PRIORITY_CHOICES, coerce=int, initial=1,
    )

    def __init__(self, *args, project, policy=None, **kwargs):
        self.project = project
        self.policy = policy
        self.unreadable_rules = []
        if policy is not None and 'initial' not in kwargs:
            kwargs['initial'] = self._initial_from(policy)
        super().__init__(*args, **kwargs)

    def _initial_from(self, policy):
        """Fill the fields from a saved policy, noting any stored rule that cannot be read."""
        initial = {'name': policy.name, 'use_gender_rule': False}
        for data in policy.rules:
            try:
                rule = rule_from_dict(data)
            except (ValueError, TypeError, AttributeError):
                self.unreadable_rules.append(data.get('key') if isinstance(data, dict) else str(data))
                continue
            if isinstance(rule, TeamSizeRule):
                initial.update(min_size=rule.min_size, max_size=rule.max_size)
            elif isinstance(rule, GenderRule):
                initial.update(use_gender_rule=True, gender_priority=rule.priority)
        return initial

    def clean_name(self):
        name = self.cleaned_data['name']
        others = self.project.policies.filter(name__iexact=name)
        if self.policy is not None:
            others = others.exclude(pk=self.policy.pk)
        if others.exists():
            raise forms.ValidationError('This project already has a policy with this name.')
        return name

    def clean(self):
        cleaned_data = super().clean()
        min_size, max_size = cleaned_data.get('min_size'), cleaned_data.get('max_size')
        if min_size is not None and max_size is not None and max_size < min_size:
            self.add_error('max_size', 'The largest team size must be at least the smallest.')
        return cleaned_data

    def build_rules(self):
        """Return the rules chosen in the form. Call only after is_valid()."""
        data = self.cleaned_data
        rules = [TeamSizeRule(data['min_size'], data['max_size'])]
        if data['use_gender_rule']:
            rules.append(GenderRule(priority=data['gender_priority']))
        return rules

    def save(self):
        """Create or update the policy with the chosen rules, and return it."""
        rules = [rule.to_dict() for rule in self.build_rules()]
        if self.policy is None:
            return self.project.policies.create(name=self.cleaned_data['name'], rules=rules)
        self.policy.name = self.cleaned_data['name']
        self.policy.rules = rules
        self.policy.save()
        return self.policy


class LogInForm(BootstrapFormMixin, AuthenticationForm):
    """Form to log in with a username and password."""


class PasswordForm(BootstrapFormMixin, PasswordChangeForm):
    """Form for a logged in user to change their own password."""

    # Replace Django's new_password1 and new_password2 fields with clearer names.
    new_password1 = None
    new_password2 = None
    new_password, new_password_confirmation = SetPasswordMixin.create_password_fields(
        label1='New password', label2='New password confirmation'
    )
    field_order = ['old_password', 'new_password', 'new_password_confirmation']

    def clean(self):
        self.validate_passwords('new_password', 'new_password_confirmation')
        self.validate_password_for_user(self.user, 'new_password_confirmation')
        return super().clean()

    def save(self, commit=True):
        return self.set_password_and_save(self.user, 'new_password', commit=commit)


class ProfileForm(BootstrapFormMixin, forms.ModelForm):
    """Form for a logged in user to edit their own profile."""

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']


class UserCreateForm(BootstrapFormMixin, UserCreationForm):
    """Form for a superuser to create a new user, including a password."""

    # Replace Django's password1 and password2 fields with clearer names.
    password1 = None
    password2 = None
    password, password_confirmation = SetPasswordMixin.create_password_fields()

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_superuser']

    def validate_passwords(self, password1_field_name='password', password2_field_name='password_confirmation'):
        super().validate_passwords(password1_field_name, password2_field_name)

    def validate_password_for_user(self, user, password_field_name='password_confirmation'):
        super().validate_password_for_user(user, password_field_name)

    def set_password_and_save(self, user, password_field_name='password', commit=True):
        return super().set_password_and_save(user, password_field_name, commit)


class UserUpdateForm(BootstrapFormMixin, forms.ModelForm):
    """Form for a superuser to update the details of any user."""

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_superuser']


class ProjectForm(BootstrapFormMixin, forms.ModelForm):
    """Form to create or edit a project."""

    class Meta:
        model = Project
        fields = ['name', 'description']
