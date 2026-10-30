from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from allocations.models import User
from allocations.tests.helpers import PASSWORD, create_user


class UserModelTestCase(TestCase):
    """Tests of the User model."""

    def setUp(self):
        self.user = create_user()

    def assert_user_is_valid(self):
        try:
            self.user.full_clean()
        except ValidationError:
            self.fail('The user should be valid.')

    def assert_user_is_invalid(self):
        with self.assertRaises(ValidationError):
            self.user.full_clean()

    def test_user_model_is_the_active_user_model(self):
        self.assertIs(get_user_model(), User)

    def test_valid_user(self):
        self.assert_user_is_valid()

    # Username

    def test_username_must_not_be_blank(self):
        self.user.username = ''
        self.assert_user_is_invalid()

    def test_username_may_contain_150_characters(self):
        self.user.username = 'x' * 150
        self.assert_user_is_valid()

    def test_username_must_not_contain_more_than_150_characters(self):
        self.user.username = 'x' * 151
        self.assert_user_is_invalid()

    def test_username_may_contain_letters_digits_and_the_symbols_at_dot_plus_dash_underscore(self):
        self.user.username = 'john.doe+test-1_x@kcl'
        self.assert_user_is_valid()

    def test_username_must_not_contain_spaces(self):
        self.user.username = 'john doe'
        self.assert_user_is_invalid()

    def test_username_must_not_contain_other_symbols(self):
        self.user.username = 'john!doe'
        self.assert_user_is_invalid()

    def test_username_must_be_unique(self):
        other_user = create_user('janedoe', 'Jane', 'Doe')
        self.user.username = other_user.username
        self.assert_user_is_invalid()

    # First name

    def test_first_name_must_not_be_blank(self):
        self.user.first_name = ''
        self.assert_user_is_invalid()

    def test_first_name_may_contain_50_characters(self):
        self.user.first_name = 'x' * 50
        self.assert_user_is_valid()

    def test_first_name_must_not_contain_more_than_50_characters(self):
        self.user.first_name = 'x' * 51
        self.assert_user_is_invalid()

    def test_first_name_need_not_be_unique(self):
        create_user('johnsmith', 'John', 'Smith')
        self.assert_user_is_valid()

    # Last name

    def test_last_name_must_not_be_blank(self):
        self.user.last_name = ''
        self.assert_user_is_invalid()

    def test_last_name_may_contain_50_characters(self):
        self.user.last_name = 'x' * 50
        self.assert_user_is_valid()

    def test_last_name_must_not_contain_more_than_50_characters(self):
        self.user.last_name = 'x' * 51
        self.assert_user_is_invalid()

    def test_last_name_need_not_be_unique(self):
        create_user('janedoe', 'Jane', 'Doe')
        self.assert_user_is_valid()

    # Email

    def test_email_must_not_be_blank(self):
        self.user.email = ''
        self.assert_user_is_invalid()

    def test_email_must_contain_an_at_symbol(self):
        self.user.email = 'johndoe.example.org'
        self.assert_user_is_invalid()

    def test_email_must_contain_a_username(self):
        self.user.email = '@example.org'
        self.assert_user_is_invalid()

    def test_email_must_contain_a_domain(self):
        self.user.email = 'johndoe@'
        self.assert_user_is_invalid()

    def test_email_must_not_contain_more_than_one_at_symbol(self):
        self.user.email = 'john@doe@example.org'
        self.assert_user_is_invalid()

    def test_email_must_be_unique(self):
        other_user = create_user('janedoe', 'Jane', 'Doe')
        self.user.email = other_user.email
        self.assert_user_is_invalid()

    # Password and superuser status

    def test_password_is_not_stored_as_plain_text(self):
        self.assertNotEqual(self.user.password, PASSWORD)
        self.assertNotIn(PASSWORD, self.user.password)

    def test_check_password_accepts_the_right_password(self):
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_check_password_rejects_a_wrong_password(self):
        self.assertFalse(self.user.check_password('WrongPassword123'))

    def test_new_user_is_not_a_superuser_by_default(self):
        user = User.objects.create_user(
            username='alicechen',
            first_name='Alice',
            last_name='Chen',
            email='alicechen@example.org',
            password=PASSWORD,
        )
        self.assertFalse(user.is_superuser)

    # Methods and ordering

    def test_full_name(self):
        self.assertEqual(self.user.get_full_name(), 'John Doe')

    def test_str_shows_full_name_and_username(self):
        self.assertEqual(str(self.user), 'John Doe (johndoe)')

    def test_users_are_ordered_by_last_name_then_first_name(self):
        create_user('alicesmith', 'Alice', 'Smith')
        create_user('alicechen', 'Alice', 'Chen')
        create_user('benchen', 'Ben', 'Chen')
        usernames = [user.username for user in User.objects.all()]
        self.assertEqual(usernames, ['alicechen', 'benchen', 'johndoe', 'alicesmith'])
