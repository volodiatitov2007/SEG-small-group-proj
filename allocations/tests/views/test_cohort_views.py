"""Tests of the cohort views in allocations/views/cohort_views.py."""

from django.test import TestCase
from django.urls import reverse

from allocations.models import Cohort, Project, Student
from allocations.tests.helpers import create_superuser, create_user, log_in_url_for


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
