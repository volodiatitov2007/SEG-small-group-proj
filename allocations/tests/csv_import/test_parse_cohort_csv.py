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
        self.assertEqual(result.file_errors, [])

    def test_missing_email_column_is_an_error(self):
        result = parse_cohort_csv(csv_file('first_name,last_name\nAda,Lovelace\n'))
        self.assertEqual(len(result.file_errors), 1)
        self.assertEqual(result.file_errors[0].column, 'email')

    def test_missing_all_required_columns_gives_three_errors(self):
        result = parse_cohort_csv(csv_file('gender,c-score\n1: Woman,60\n'))
        self.assertEqual(len(result.file_errors), 3)

    def test_file_with_only_required_columns_has_no_errors(self):
        result = parse_cohort_csv(csv_file('first_name,last_name,email\nAda,Lovelace,ada@example.org\n'))
        self.assertEqual(result.file_errors, [])

    def test_extra_columns_are_accepted(self):
        result = parse_cohort_csv(csv_file('first_name,last_name,email,favourite_colour\n'
                                           'Ada,Lovelace,ada@example.org,blue\n'))
        self.assertEqual(result.file_errors, [])

    def test_bom_at_start_of_file_is_ignored(self):
        result = parse_cohort_csv(csv_file('\ufefffirst_name,last_name,email\nAda,Lovelace,ada@example.org\n'))
        self.assertEqual(result.file_errors, [])


class RequiredValuesTestCase(SimpleTestCase):
    """Tests that every row has a first name, last name and email."""

    def test_blank_email_is_an_error_with_its_row_number(self):
        result = parse_cohort_csv(csv_file('first_name,last_name,email\nAda,Lovelace,\n'))
        self.assertEqual(len(result.bad_rows), 1)
        self.assertEqual(result.bad_rows[0].row_number, 2)
        self.assertEqual(result.bad_rows[0].column, 'email')

    def test_value_of_only_spaces_counts_as_blank(self):
        result = parse_cohort_csv(csv_file('first_name,last_name,email\n   ,Lovelace,ada@example.org\n'))
        self.assertEqual(len(result.bad_rows), 1)
        self.assertEqual(result.bad_rows[0].column, 'first_name')

    def test_every_blank_value_is_reported(self):
        result = parse_cohort_csv(csv_file(
            'first_name,last_name,email\n'
            'Ada,,ada@example.org\n'
            ',Turing,\n'
        ))
        self.assertEqual([error.row_number for error in result.bad_rows], [2, 3, 3])

    def test_short_row_counts_as_missing_values(self):
        result = parse_cohort_csv(csv_file('first_name,last_name,email\nAda\n'))
        self.assertEqual([error.column for error in result.bad_rows], ['last_name', 'email'])

    def test_rows_are_not_checked_when_a_column_is_missing(self):
        result = parse_cohort_csv(csv_file('first_name,last_name\n,\n'))
        self.assertEqual(len(result.file_errors), 1)
        self.assertEqual(result.file_errors[0].column, 'email')


class EmailTestCase(SimpleTestCase):
    """Tests that emails are valid and not used twice."""

    def test_invalid_email_is_an_error(self):
        result = parse_cohort_csv(csv_file('first_name,last_name,email\nBob,Brown,bob@\n'))
        self.assertEqual(len(result.bad_rows), 1)
        self.assertEqual(result.bad_rows[0].value, 'bob@')

    def test_duplicate_email_names_both_rows(self):
        result = parse_cohort_csv(csv_file(
            'first_name,last_name,email\n'
            'Ada,Lovelace,ada@example.org\n'
            'Ann,Lee,ada@example.org\n'
        ))
        self.assertEqual(len(result.bad_rows), 1)
        self.assertEqual(result.bad_rows[0].row_number, 3)
        self.assertIn('row 2', result.bad_rows[0].message)

    def test_duplicate_ignores_capitals_and_spaces(self):
        result = parse_cohort_csv(csv_file(
            'first_name,last_name,email\n'
            'Ada,Lovelace,ada@example.org\n'
            'Ann,Lee, ADA@Example.org \n'
        ))
        self.assertEqual(len(result.bad_rows), 1)

    def test_blank_email_is_only_reported_once(self):
        result = parse_cohort_csv(csv_file('first_name,last_name,email\nAda,Lovelace,\n'))
        self.assertEqual(len(result.bad_rows), 1)

    def test_different_emails_are_fine(self):
        result = parse_cohort_csv(csv_file(
            'first_name,last_name,email\n'
            'Ada,Lovelace,ada@example.org\n'
            'Alan,Turing,alan@example.org\n'
        ))
        self.assertEqual(result.bad_rows, [])


class CodedColumnsTestCase(SimpleTestCase):
    """Tests that gender and ethnicity use the allowed codes."""

    HEADER = 'first_name,last_name,email,gender,ethnicity\n'

    def parse_row(self, gender, ethnicity):
        return parse_cohort_csv(csv_file(self.HEADER + f'Ada,Lovelace,ada@example.org,{gender},{ethnicity}\n'))

    def test_code_with_label_is_valid(self):
        result = self.parse_row('1: Woman', '4: White')
        self.assertEqual(result.bad_rows, [])

    def test_space_before_the_colon_is_valid(self):
        result = self.parse_row('2: Man', '5 : Other ethnic group (e.g. Arab)')
        self.assertEqual(result.bad_rows, [])

    def test_zero_means_not_provided_and_is_valid(self):
        result = self.parse_row('0', '0')
        self.assertEqual(result.bad_rows, [])
        self.assertEqual(result.warnings, [])

    def test_unknown_code_is_an_error(self):
        result = self.parse_row('7: Robot', '1: Asian')
        self.assertEqual(len(result.bad_rows), 1)
        self.assertEqual(result.bad_rows[0].column, 'gender')
        self.assertEqual(result.bad_rows[0].value, '7: Robot')

    def test_value_without_a_number_is_an_error(self):
        result = self.parse_row('2: Man', 'Asian')
        self.assertEqual(len(result.bad_rows), 1)
        self.assertEqual(result.bad_rows[0].column, 'ethnicity')

    def test_blank_code_is_a_warning_not_an_error(self):
        result = self.parse_row('', '4: White')
        self.assertEqual(result.bad_rows, [])
        self.assertEqual(len(result.warnings), 1)
        self.assertEqual(result.warnings[0].column, 'gender')

    def test_file_without_coded_columns_is_fine(self):
        result = parse_cohort_csv(csv_file('first_name,last_name,email\nAda,Lovelace,ada@example.org\n'))
        self.assertEqual(result.bad_rows, [])
        self.assertEqual(result.warnings, [])


class CScoreTestCase(SimpleTestCase):
    """Tests that c-scores are whole numbers from 0 to 100."""

    def parse_c_score(self, c_score):
        return parse_cohort_csv(csv_file(
            'first_name,last_name,email,c-score\n'
            f'Ada,Lovelace,ada@example.org,{c_score}\n'
        ))

    def test_whole_numbers_from_0_to_100_are_valid(self):
        for c_score in ['0', '57', '100', ' 57 ']:
            with self.subTest(c_score=c_score):
                self.assertEqual(self.parse_c_score(c_score).bad_rows, [])

    def test_invalid_values_are_errors(self):
        for c_score in ['101', '-5', '55.5', 'abc']:
            with self.subTest(c_score=c_score):
                result = self.parse_c_score(c_score)
                self.assertEqual(len(result.bad_rows), 1)
                self.assertEqual(result.bad_rows[0].value, c_score)

    def test_blank_c_score_is_a_warning_not_an_error(self):
        result = self.parse_c_score('')
        self.assertEqual(result.bad_rows, [])
        self.assertEqual(len(result.warnings), 1)
        self.assertEqual(result.warnings[0].column, 'c-score')

    def test_file_without_c_score_column_is_fine(self):
        result = parse_cohort_csv(csv_file('first_name,last_name,email\nAda,Lovelace,ada@example.org\n'))
        self.assertEqual(result.bad_rows, [])
        self.assertEqual(result.warnings, [])


class CleanRowsTestCase(SimpleTestCase):
    """Tests that good rows come out as clean dicts, ready to save as students."""

    HEADER = 'first_name,last_name,email,gender,ethnicity,c-score,schedule\n'

    def test_sample_file_gives_300_good_rows(self):
        with open(FIXTURES / 'sample_student_cohort_data.csv', 'rb') as file:
            result = parse_cohort_csv(file)
        self.assertEqual(len(result.rows), 300)
        self.assertEqual(result.bad_rows, [])

    def test_good_row_becomes_a_clean_dict(self):
        result = parse_cohort_csv(csv_file(self.HEADER + ' Ada , Lovelace , ADA@Example.org ,1: Woman,4: White,57,1: Yes\n'))
        self.assertEqual(result.rows, [{
            'first_name': 'Ada',
            'last_name': 'Lovelace',
            'email': 'ada@example.org',
            'gender': 1,
            'ethnicity': 4,
            'c_score': 57,
            'extra': {'schedule': '1: Yes'},
        }])

    def test_bad_row_is_skipped_and_good_rows_are_kept(self):
        result = parse_cohort_csv(csv_file(
            self.HEADER
            + 'Ada,Lovelace,ada@example.org,1,4,57,\n'
            + 'Bob,Brown,bob@example.org,9,4,57,\n'
            + 'Alan,Turing,alan@example.org,2,4,60,\n'
        ))
        self.assertEqual([student['first_name'] for student in result.rows], ['Ada', 'Alan'])
        self.assertEqual([problem.row_number for problem in result.bad_rows], [3])

    def test_blank_values_become_0_for_codes_and_none_for_c_score(self):
        result = parse_cohort_csv(csv_file(self.HEADER + 'Ada,Lovelace,ada@example.org,,,,\n'))
        student = result.rows[0]
        self.assertEqual(student['gender'], 0)
        self.assertEqual(student['ethnicity'], 0)
        self.assertIsNone(student['c_score'])

    def test_missing_columns_become_none(self):
        result = parse_cohort_csv(csv_file('first_name,last_name,email\nAda,Lovelace,ada@example.org\n'))
        student = result.rows[0]
        self.assertIsNone(student['gender'])
        self.assertIsNone(student['ethnicity'])
        self.assertIsNone(student['c_score'])
        self.assertEqual(student['extra'], {})

    def test_duplicate_email_keeps_the_first_row(self):
        result = parse_cohort_csv(csv_file(
            'first_name,last_name,email\n'
            'Ada,Lovelace,ada@example.org\n'
            'Ann,Lee,ada@example.org\n'
        ))
        self.assertEqual([student['first_name'] for student in result.rows], ['Ada'])

    def test_email_of_a_bad_row_can_be_used_again(self):
        result = parse_cohort_csv(csv_file(
            self.HEADER
            + 'Ada,Lovelace,ada@example.org,9,4,57,\n'
            + 'Ada,Lovelace,ada@example.org,1,4,57,\n'
        ))
        self.assertEqual(len(result.rows), 1)
        self.assertEqual(result.rows[0]['gender'], 1)
        self.assertEqual([problem.row_number for problem in result.bad_rows], [2])

    def test_no_rows_when_a_required_column_is_missing(self):
        result = parse_cohort_csv(csv_file('first_name,last_name\nAda,Lovelace\n'))
        self.assertEqual(result.rows, [])
