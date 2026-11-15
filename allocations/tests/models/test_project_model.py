from django.core.exceptions import ValidationError
from django.test import TestCase

from allocations.models import Project
from allocations.tests.helpers import create_user


class ProjectModelTestCase(TestCase):
    """Tests of the Project model."""

    def setUp(self):
        self.owner = create_user()
        self.project = Project.objects.create(name='SEG Small Group 2026', owner=self.owner)

    def assert_project_is_valid(self):
        try:
            self.project.full_clean()
        except ValidationError:
            self.fail('The project should be valid.')

    def assert_project_is_invalid(self):
        with self.assertRaises(ValidationError):
            self.project.full_clean()

    def test_valid_project(self):
        self.assert_project_is_valid()

    def test_name_must_not_be_blank(self):
        self.project.name = ''
        self.assert_project_is_invalid()

    def test_name_may_contain_100_characters(self):
        self.project.name = 'x' * 100
        self.assert_project_is_valid()

    def test_name_must_not_contain_more_than_100_characters(self):
        self.project.name = 'x' * 101
        self.assert_project_is_invalid()

    def test_description_may_be_blank(self):
        self.project.description = ''
        self.assert_project_is_valid()

    def test_string_is_the_name(self):
        self.assertEqual(str(self.project), 'SEG Small Group 2026')

    def test_owner_must_not_be_missing(self):
        self.project.owner = None
        self.assert_project_is_invalid()
