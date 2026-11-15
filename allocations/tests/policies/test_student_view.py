from types import SimpleNamespace

from django.test import SimpleTestCase

from allocations.policies import StudentView, student_view


def make_row(**changes):
    """Make a stand-in for a Student row with the fields the converter reads."""
    fields = {
        'id': 7, 'first_name': 'Rahul', 'last_name': 'Khan', 'gender': 2, 'ethnicity': 1,
        'c_score': 57, 'extra': {'schedule': '1: Yes'},
    }
    return SimpleNamespace(**{**fields, **changes})


class StudentViewConverterTestCase(SimpleTestCase):
    """Tests of student_view(), which turns a stored student into a StudentView."""

    def test_copies_every_field(self):
        view = student_view(make_row())
        expected = StudentView(id=7, name='Rahul Khan', gender=2, ethnicity=1, c_score=57)
        self.assertEqual(view, expected)
        self.assertEqual(view.extra, {'schedule': '1: Yes'})

    def test_missing_values_stay_none(self):
        view = student_view(make_row(gender=None, ethnicity=None, c_score=None))
        self.assertIsNone(view.gender)
        self.assertIsNone(view.ethnicity)
        self.assertIsNone(view.c_score)

    def test_not_provided_gender_stays_zero(self):
        self.assertEqual(student_view(make_row(gender=0)).gender, 0)

    def test_missing_extra_becomes_empty_dict(self):
        self.assertEqual(student_view(make_row(extra=None)).extra, {})

    def test_extra_is_copied_not_shared(self):
        row = make_row()
        view = student_view(row)
        row.extra['schedule'] = '2: No'
        self.assertEqual(view.extra, {'schedule': '1: Yes'})

    def test_name_has_no_stray_spaces_when_a_name_is_blank(self):
        self.assertEqual(student_view(make_row(last_name='')).name, 'Rahul')
