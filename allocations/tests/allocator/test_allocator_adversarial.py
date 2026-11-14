from django.test import TestCase

from allocations.allocator import allocate
from allocations.policies import TeamSizeRule
from allocations.tests.allocator.helpers import (
    FakeAttainmentSpreadRule, FakeGenderRule, assert_ok_invariants, make_students,
)


class AdversarialCohortTestCase(TestCase):
    """Tests of edge-case cohorts under fake gender and attainment soft rules."""

    def setUp(self):
        self.size_rule = TeamSizeRule(min_size=4, max_size=5)
        self.gender_rule = FakeGenderRule()
        self.spread_rule = FakeAttainmentSpreadRule(max_spread=3)

    def allocate(self, students):
        rules = [self.size_rule, self.gender_rule, self.spread_rule]
        result = allocate(students, rules, seed=9)
        assert_ok_invariants(self, result, students, rules)
        return result

    def gender_violations(self, result):
        return [v for v in result.violations if v.rule == 'fake_gender']

    def spread_violations(self, result):
        return [v for v in result.violations if v.rule == 'fake_spread']

    def test_cohort_of_one_disclosed_gender_has_no_gender_violations(self):
        result = self.allocate(make_students(20, genders=[1] * 20, c_scores=[4] * 20))
        self.assertEqual(self.gender_violations(result), [])

    def test_single_non_binary_student_yields_exactly_one_gender_violation(self):
        genders = [1] * 20
        genders[6] = 3
        result = self.allocate(make_students(20, genders=genders, c_scores=[4] * 20))
        self.assertEqual(len(self.gender_violations(result)), 1)

    def test_all_undisclosed_genders_produce_no_gender_violations(self):
        result = self.allocate(make_students(20, genders=[0] * 20, c_scores=[4] * 20))
        self.assertEqual(self.gender_violations(result), [])

    def test_mixed_absent_and_undisclosed_genders_are_both_ignored(self):
        genders = [None, 0] * 10
        result = self.allocate(make_students(20, genders=genders, c_scores=[4] * 20))
        self.assertEqual(self.gender_violations(result), [])

    def test_all_equal_c_scores_produce_no_spread_violations(self):
        result = self.allocate(make_students(20, genders=[1] * 20, c_scores=[7] * 20))
        self.assertEqual(self.spread_violations(result), [])

    def test_all_c_scores_none_produce_no_spread_violations(self):
        result = self.allocate(make_students(20, genders=[1] * 20, c_scores=[None] * 20))
        self.assertEqual(self.spread_violations(result), [])


class ReferenceTimingTestCase(TestCase):
    """Tests the documented reference workload finishes within its time limit."""

    def setUp(self):
        self.size_rule = TeamSizeRule(min_size=4, max_size=5)

    def test_300_students_with_two_soft_rules_finishes_ok_within_15_seconds(self):
        students = make_students(
            300,
            genders=[(index % 4) for index in range(300)],
            c_scores=[(index * 13) % 50 for index in range(300)],
        )
        rules = [self.size_rule, FakeGenderRule(), FakeAttainmentSpreadRule(max_spread=5)]
        result = allocate(students, rules, time_limit=15)
        self.assertEqual(result.status, 'ok')
        self.assertLess(result.duration_seconds, 15 + 1.5)
        assert_ok_invariants(self, result, students, rules)
