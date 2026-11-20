"""Boundary and adversarial cohorts: sizes at the limits and awkward attribute values."""
from django.test import SimpleTestCase

from allocations.allocator import INFEASIBLE
from allocations.tests.allocator.helpers import assert_empty_non_ok_result, assert_ok_invariants
from allocations.tests.factories import MISSING, make_cohort, make_policy, run_allocation


class SizeBoundaryTestCase(SimpleTestCase):
    """Team size 4 to 5, with cohorts just below, at and just above each limit."""

    def test_cohort_sizes_around_the_limits(self):
        # n -> can it be split into teams of 4 to 5?
        expected = {0: False, 1: False, 3: False, 4: True, 5: True, 6: False, 7: False,
                    8: True, 10: True, 11: False, 12: True, 15: True, 16: True, 19: True}
        policy = make_policy()
        for n, feasible in expected.items():
            with self.subTest(n=n):
                cohort = make_cohort(n, seed=n)
                result = run_allocation(cohort, policy)
                if feasible:
                    assert_ok_invariants(self, result, cohort, policy)
                else:
                    self.assertEqual(result.status, INFEASIBLE)
                    assert_empty_non_ok_result(self, result)


class AdversarialCohortTestCase(SimpleTestCase):
    """Awkward attribute values must never lose, duplicate or reject students."""

    SIZES = [4, 5, 9, 13, 23, 60, 101]

    def check_all_sizes(self, **attributes):
        """Allocate cohorts of every size in SIZES; an attribute may be a function of the size n."""
        policy = make_policy()
        for n in self.SIZES:
            resolved = {name: value(n) if callable(value) else value for name, value in attributes.items()}
            with self.subTest(n=n):
                cohort = make_cohort(n, seed=n, **resolved)
                assert_ok_invariants(self, run_allocation(cohort, policy), cohort, policy)

    def test_everyone_the_same_gender(self):
        self.check_all_sizes(genders=1)

    def test_nobody_has_disclosed_a_gender(self):
        self.check_all_sizes(genders=0)

    def test_the_gender_column_is_missing(self):
        self.check_all_sizes(genders=MISSING)

    def test_everyone_has_the_same_c_score(self):
        self.check_all_sizes(c_scores=50)

    def test_nobody_has_a_c_score(self):
        self.check_all_sizes(c_scores=MISSING)

    def test_only_the_lowest_and_highest_c_scores(self):
        self.check_all_sizes(c_scores=lambda n: [0 if i % 2 else 100 for i in range(n)])

    def test_a_single_non_binary_student_is_reported_as_isolated(self):
        policy = make_policy()
        for n in self.SIZES:
            with self.subTest(n=n):
                genders = [3] + [1 if i % 2 else 2 for i in range(n - 1)]
                cohort = make_cohort(n, seed=n, genders=genders)
                result = run_allocation(cohort, policy)
                assert_ok_invariants(self, result, cohort, policy)
                lone = [v for v in result.violations if v.rule == 'fake_gender' and 'gender-3' in v.message]
                self.assertEqual(len(lone), 1, 'The only non-binary student must be reported as isolated.')
