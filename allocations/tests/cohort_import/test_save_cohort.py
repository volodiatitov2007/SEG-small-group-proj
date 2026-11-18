"""Tests of save_cohort in allocations/cohort_import.py."""

from pathlib import Path

from django.db import IntegrityError
from django.test import TestCase

from allocations.cohort_import import save_cohort
from allocations.csv_import import ImportResult, parse_cohort_csv
from allocations.models import Cohort, Project, Student
from allocations.tests.helpers import create_user

FIXTURES = Path(__file__).resolve().parent.parent / 'fixtures' / 'csv'


def student_row(email='ada@example.org', **changes):
    """Return a clean row like the ones parse_cohort_csv makes."""
    row = {
        'first_name': 'Ada',
        'last_name': 'Lovelace',
        'email': email,
        'gender': 1,
        'ethnicity': 4,
        'c_score': 57,
        'extra': {'schedule': '1: Yes'},
    }
    row.update(changes)
    return row


class SaveCohortTestCase(TestCase):
    """Tests of saving the good rows of a cohort file."""

    def setUp(self):
        self.project = Project.objects.create(name='SEG 2026', owner=create_user())
        self.result = ImportResult(
            rows=[student_row(), student_row(email='alan@example.org', first_name='Alan', c_score=None)],
            columns=['first_name', 'last_name', 'email', 'gender', 'ethnicity', 'c-score', 'schedule'],
        )

    def test_creates_a_cohort_for_the_project(self):
        cohort = save_cohort(self.project, 'cohort.csv', self.result)
        self.assertEqual(cohort.project, self.project)
        self.assertEqual(cohort.original_filename, 'cohort.csv')
        self.assertEqual(cohort.columns, self.result.columns)

    def test_saves_one_student_per_row(self):
        cohort = save_cohort(self.project, 'cohort.csv', self.result)
        self.assertEqual(cohort.students.count(), 2)

    def test_saves_every_field_of_the_row(self):
        cohort = save_cohort(self.project, 'cohort.csv', self.result)
        student = cohort.students.get(email='ada@example.org')
        self.assertEqual(student.first_name, 'Ada')
        self.assertEqual(student.last_name, 'Lovelace')
        self.assertEqual(student.gender, 1)
        self.assertEqual(student.ethnicity, 4)
        self.assertEqual(student.c_score, 57)
        self.assertEqual(student.extra, {'schedule': '1: Yes'})

    def test_blank_c_score_is_saved_as_none(self):
        cohort = save_cohort(self.project, 'cohort.csv', self.result)
        self.assertIsNone(cohort.students.get(email='alan@example.org').c_score)

    def test_sample_file_saves_300_students(self):
        with open(FIXTURES / 'sample_student_cohort_data.csv', 'rb') as file:
            result = parse_cohort_csv(file)
        cohort = save_cohort(self.project, 'sample.csv', result)
        self.assertEqual(cohort.students.count(), 300)

    def test_nothing_is_saved_if_a_student_cannot_be_saved(self):
        self.result.rows.append(student_row())
        with self.assertRaises(IntegrityError):
            save_cohort(self.project, 'cohort.csv', self.result)
        self.assertEqual(Cohort.objects.count(), 0)
        self.assertEqual(Student.objects.count(), 0)
