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
        result = parse_cohort_csv(csv_file('first_name,last_name,email,favourite_colour\n'
                                           'Ada,Lovelace,ada@example.org,blue\n'))
        self.assertEqual(result.errors, [])

    def test_bom_at_start_of_file_is_ignored(self):
        result = parse_cohort_csv(csv_file('\ufefffirst_name,last_name,email\nAda,Lovelace,ada@example.org\n'))
        self.assertEqual(result.errors, [])


class RequiredValuesTestCase(SimpleTestCase):
    """Tests that every row has a first name, last name and email."""

    def test_blank_email_is_an_error_with_its_row_number(self):
        result = parse_cohort_csv(csv_file('first_name,last_name,email\nAda,Lovelace,\n'))
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0].row_number, 2)
        self.assertEqual(result.errors[0].column, 'email')

    def test_value_of_only_spaces_counts_as_blank(self):
        result = parse_cohort_csv(csv_file('first_name,last_name,email\n   ,Lovelace,ada@example.org\n'))
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0].column, 'first_name')

    def test_every_blank_value_is_reported(self):
        result = parse_cohort_csv(csv_file(
            'first_name,last_name,email\n'
            'Ada,,ada@example.org\n'
            ',Turing,\n'
        ))
        self.assertEqual([error.row_number for error in result.errors], [2, 3, 3])

    def test_short_row_counts_as_missing_values(self):
        result = parse_cohort_csv(csv_file('first_name,last_name,email\nAda\n'))
        self.assertEqual([error.column for error in result.errors], ['last_name', 'email'])

    def test_rows_are_not_checked_when_a_column_is_missing(self):
        result = parse_cohort_csv(csv_file('first_name,last_name\n,\n'))
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0].column, 'email')
