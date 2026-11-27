"""Tests of the cohort views in allocations/views/cohort_views.py."""

from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from allocations.models import Cohort, Project, Student
from allocations.tests.helpers import create_superuser, create_user, log_in_url_for, messages_in

FIXTURES = Path(__file__).resolve().parent.parent / 'fixtures' / 'csv'


class CohortDetailViewTestCase(TestCase):
    """Tests of the page that shows the students in a cohort."""

    def setUp(self):
        self.user = create_user()
        project = Project.objects.create(name='SEG 2026', owner=self.user)
        self.cohort = Cohort.objects.create(project=project, original_filename='cohort.csv')
        Student.objects.create(
            cohort=self.cohort, first_name='Ada', last_name='Lovelace', email='ada@example.org',
            gender=1, ethnicity=4, c_score=57,
        )
        self.url = reverse('cohort_detail', args=[self.cohort.id])
        self.client.force_login(self.user)

    def test_cohort_detail_url(self):
        self.assertEqual(self.url, f'/cohorts/{self.cohort.id}/')

    def test_logged_out_user_is_redirected_to_log_in(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertRedirects(response, log_in_url_for(self.url))

    def test_page_shows_the_cohort_and_its_students(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'cohort_detail.html')
        self.assertContains(response, 'cohort.csv')
        self.assertContains(response, 'Ada Lovelace')
        self.assertContains(response, 'ada@example.org')
        self.assertContains(response, '1 student</p>')

    def test_page_links_back_to_the_project(self):
        response = self.client.get(self.url)
        self.assertContains(response, reverse('project_detail', args=[self.cohort.project.id]))

    def test_missing_c_score_is_shown_as_a_dash(self):
        Student.objects.filter(email='ada@example.org').update(c_score=None)
        response = self.client.get(self.url)
        self.assertContains(response, '<td>—</td>', html=True)

    def test_other_users_cohort_gives_404(self):
        other_project = Project.objects.create(name='Theirs', owner=create_superuser())
        other_cohort = Cohort.objects.create(project=other_project, original_filename='theirs.csv')
        response = self.client.get(reverse('cohort_detail', args=[other_cohort.id]))
        self.assertEqual(response.status_code, 404)

    def test_missing_cohort_gives_404(self):
        response = self.client.get(reverse('cohort_detail', args=[999]))
        self.assertEqual(response.status_code, 404)


class CohortUploadViewTestCase(TestCase):
    """Tests of uploading a cohort CSV file to a project."""

    def setUp(self):
        self.user = create_user()
        self.project = Project.objects.create(name='SEG 2026', owner=self.user)
        self.url = reverse('cohort_upload', args=[self.project.id])
        self.client.force_login(self.user)

    def upload(self, text, name='cohort.csv', **kwargs):
        """Post CSV text to the upload page as if it were a file."""
        file = SimpleUploadedFile(name, text.encode('utf-8'), content_type='text/csv')
        return self.client.post(self.url, {'file': file}, **kwargs)

    def test_cohort_upload_url(self):
        self.assertEqual(self.url, f'/projects/{self.project.id}/upload/')

    def test_logged_out_user_is_redirected_to_log_in(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertRedirects(response, log_in_url_for(self.url))

    def test_get_shows_the_upload_form(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'cohort_upload.html')
        self.assertContains(response, 'enctype="multipart/form-data"')
        self.assertEqual(Cohort.objects.count(), 0)

    def test_good_file_saves_a_cohort_with_its_students(self):
        self.upload('first_name,last_name,email\nAda,Lovelace,ada@example.org\nAlan,Turing,alan@example.org\n')
        cohort = Cohort.objects.get()
        self.assertEqual(cohort.project, self.project)
        self.assertEqual(cohort.original_filename, 'cohort.csv')
        self.assertEqual(cohort.students.count(), 2)

    def test_extra_columns_are_kept_for_each_student(self):
        self.upload(
            'first_name,last_name,email,schedule\n'
            'Ada,Lovelace,ada@example.org,1: Yes\n'
            'Alan,Turing,alan@example.org,2: No\n'
            'Grace,Hopper,grace@example.org,1: Yes\n'
            'Katherine,Johnson,katherine@example.org,2: No\n'
            'Tim,Berners-Lee,tim@example.org,1: Yes\n'
        )
        self.assertEqual(Student.objects.count(), 5)
        self.assertEqual(Student.objects.get(email='alan@example.org').extra, {'schedule': '2: No'})

    def test_blank_c_score_is_saved_as_none_with_a_warning(self):
        response = self.upload('first_name,last_name,email,c-score\nAda,Lovelace,ada@example.org,\n', follow=True)
        self.assertIsNone(Student.objects.get().c_score)
        self.assertContains(response, '1 warning</summary>')
        self.assertContains(response, 'c-score is blank')

    def test_good_file_redirects_to_the_cohort_with_a_message(self):
        response = self.upload('first_name,last_name,email\nAda,Lovelace,ada@example.org\n', follow=True)
        cohort = Cohort.objects.get()
        self.assertRedirects(response, reverse('cohort_detail', args=[cohort.id]))
        self.assertIn('Uploaded cohort.csv: imported 1, skipped 0.', messages_in(response))

    def test_bad_rows_are_skipped_and_listed_on_the_cohort_page(self):
        response = self.upload(
            'first_name,last_name,email\nAda,Lovelace,ada@example.org\nBob,Brown,bob@\n', follow=True
        )
        self.assertEqual(Student.objects.count(), 1)
        self.assertIn('Uploaded cohort.csv: imported 1, skipped 1.', messages_in(response))
        self.assertContains(response, 'These rows were skipped')
        self.assertContains(response, 'Row 3:')

    def test_a_row_with_two_problems_counts_as_one_skipped_row(self):
        response = self.upload(
            'first_name,last_name,email\nAda,Lovelace,ada@example.org\n,,bob@\n', follow=True
        )
        self.assertIn('Uploaded cohort.csv: imported 1, skipped 1.', messages_in(response))

    def test_upload_problems_are_only_shown_once(self):
        self.upload('first_name,last_name,email\nAda,Lovelace,ada@example.org\nBob,Brown,bob@\n', follow=True)
        response = self.client.get(reverse('cohort_detail', args=[Cohort.objects.get().id]))
        self.assertNotContains(response, 'These rows were skipped')

    def test_file_error_saves_nothing_and_is_shown(self):
        response = self.upload('first_name,last_name\nAda,Lovelace\n')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Cohort.objects.count(), 0)
        self.assertContains(response, 'Nothing was imported')
        self.assertContains(response, 'Required column')

    def test_file_with_no_good_rows_saves_nothing_and_lists_the_bad_rows(self):
        response = self.upload('first_name,last_name,email\nBob,Brown,bob@\n')
        self.assertEqual(Cohort.objects.count(), 0)
        self.assertContains(response, 'No students could be imported')
        self.assertContains(response, 'Row 2:')

    def test_file_that_is_not_csv_is_rejected(self):
        response = self.upload('first_name,last_name,email\n', name='cohort.xlsx')
        self.assertEqual(Cohort.objects.count(), 0)
        self.assertContains(response, 'Please upload a .csv file.')

    def test_sample_file_imports_300_students(self):
        with open(FIXTURES / 'sample_student_cohort_data.csv', 'rb') as file:
            self.client.post(self.url, {'file': file})
        self.assertEqual(Student.objects.count(), 300)

    def test_other_users_project_gives_404_and_saves_nothing(self):
        other_project = Project.objects.create(name='Theirs', owner=create_superuser())
        response = self.client.post(
            reverse('cohort_upload', args=[other_project.id]),
            {'file': SimpleUploadedFile('c.csv', b'first_name,last_name,email\nAda,Lovelace,ada@example.org\n')},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Cohort.objects.count(), 0)
