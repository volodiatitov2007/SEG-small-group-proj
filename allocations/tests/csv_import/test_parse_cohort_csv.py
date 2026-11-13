"""Tests of parse_cohort_csv in allocations/csv_import.py."""

import io
from pathlib import Path

from django.test import SimpleTestCase

from allocations.csv_import import parse_cohort_csv

FIXTURES = Path(__file__).resolve().parent.parent / 'fixtures' / 'csv'


def csv_file(text):
    """Turn CSV text into a file-like object, as if it had been uploaded."""
    return io.BytesIO(text.encode('utf-8'))


class RequiredColumnsTestCase(SimpleTestCase):
    """Tests that the required columns must be present."""

    def test_sample_file_has_no_errors(self):
        with open(FIXTURES / 'sample_student_cohort_data.csv', 'rb') as file:
            result = parse_cohort_csv(file)
        self.assertEqual(result.errors, [])

    def test_missing_email_column_is_an_error(self):
        result = parse_cohort_csv(csv_file('first_name,last_name\nAda,Lovelace\n'))
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0].column, 'email')

    def test_missing_all_required_columns_gives_three_errors(self):
        result = parse_cohort_csv(csv_file('gender,c-score\n1: Woman,60\n'))
        self.assertEqual(len(result.errors), 3)

    def test_file_with_only_required_columns_has_no_errors(self):
        result = parse_cohort_csv(csv_file('first_name,last_name,email\nAda,Lovelace,ada@example.org\n'))
        self.assertEqual(result.errors, [])

    def test_extra_columns_are_accepted(self):
        result = parse_cohort_csv(csv_file('first_name,last_name,email,favourite_colour\nAda,Lovelace,ada@example.org,blue\n'))
        self.assertEqual(result.errors, [])

    def test_bom_at_start_of_file_is_ignored(self):
        result = parse_cohort_csv(csv_file('\ufefffirst_name,last_name,email\nAda,Lovelace,ada@example.org\n'))
        self.assertEqual(result.errors, [])