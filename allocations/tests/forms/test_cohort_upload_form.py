"""Tests of the form used to upload a cohort CSV file."""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from allocations.forms import CohortUploadForm


def uploaded_file(name):
    """Return a small file, as if it had been uploaded with this name."""
    return SimpleUploadedFile(name, b'first_name,last_name,email\n', content_type='text/csv')


class CohortUploadFormTestCase(SimpleTestCase):
    """Tests of the form used to upload a cohort CSV file."""

    def test_form_has_one_file_field(self):
        self.assertEqual(list(CohortUploadForm().fields), ['file'])

    def test_csv_file_is_valid(self):
        form = CohortUploadForm(data={}, files={'file': uploaded_file('cohort.csv')})
        self.assertTrue(form.is_valid())

    def test_capital_letters_in_the_extension_are_fine(self):
        form = CohortUploadForm(data={}, files={'file': uploaded_file('COHORT.CSV')})
        self.assertTrue(form.is_valid())

    def test_file_that_is_not_csv_is_rejected(self):
        form = CohortUploadForm(data={}, files={'file': uploaded_file('cohort.xlsx')})
        self.assertFalse(form.is_valid())
        self.assertIn('Please upload a .csv file.', form.errors['file'])

    def test_no_file_is_rejected(self):
        form = CohortUploadForm(data={}, files={})
        self.assertFalse(form.is_valid())
        self.assertIn('This field is required.', form.errors['file'])
