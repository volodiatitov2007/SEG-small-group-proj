from django.test import TestCase

from allocations.allocator import allocate
from allocations.policies import TeamSizeRule
from allocations.tests.allocator.helpers import (
    FakeGenderRule, assert_empty_non_ok_result, assert_ok_invariants, make_students,
)


class FeasibilityTestCase(TestCase):
    """Tests of which cohorts the allocator accepts or rejects up front."""

    def setUp(self):
        self.size_rule = TeamSizeRule(min_size=4, max_size=5)

    def test_300_students_split_into_teams_of_4_or_5_is_ok(self):
        result = allocate(make_students(300), [self.size_rule])
        assert_ok_invariants(self, result, make_students(300), [self.size_rule])
        self.assertEqual(result.message, 'Allocated 300 students into 60 teams.')

    def test_8_students_split_into_teams_of_4_or_5_is_ok(self):
        result = allocate(make_students(8), [self.size_rule])
        assert_ok_invariants(self, result, make_students(8), [self.size_rule])
        self.assertEqual(result.message, 'Allocated 8 students into 2 teams.')

    def test_9_students_split_into_teams_of_4_or_5_is_ok(self):
        students = make_students(9)
        result = allocate(students, [self.size_rule])
        assert_ok_invariants(self, result, students, [self.size_rule])
        self.assertEqual(result.message, 'Allocated 9 students into 2 teams.')
        self.assertEqual([len(members) for members in result.teams.values()], [5, 4])
        self.assertEqual([student.id for student in result.teams['Team 1']], [1, 2, 3, 4, 5])
        self.assertEqual([student.id for student in result.teams['Team 2']], [6, 7, 8, 9])

    def test_7_students_cannot_be_split_into_teams_of_4_or_5(self):
        result = allocate(make_students(7), [self.size_rule])
        self.assertEqual(result.status, 'infeasible')
        self.assertEqual(result.message, '7 students cannot be split into teams of 4-5.')
        assert_empty_non_ok_result(self, result)

    def test_11_students_cannot_be_split_into_teams_of_4_or_5(self):
        result = allocate(make_students(11), [self.size_rule])
        self.assertEqual(result.status, 'infeasible')
        self.assertEqual(result.message, '11 students cannot be split into teams of 4-5.')
        assert_empty_non_ok_result(self, result)

    def test_zero_students_is_infeasible(self):
        result = allocate([], [self.size_rule])
        self.assertEqual(result.status, 'infeasible')
        self.assertEqual(result.message, 'There are no students to allocate.')
        assert_empty_non_ok_result(self, result)

    def test_fewer_students_than_the_minimum_team_size_is_infeasible(self):
        result = allocate(make_students(3), [self.size_rule])
        self.assertEqual(result.status, 'infeasible')
        self.assertEqual(result.message, '3 students cannot be split into teams of 4-5.')
        assert_empty_non_ok_result(self, result)

    def test_minimum_equal_to_maximum_with_exact_count_gives_exactly_one_team(self):
        rule = TeamSizeRule(min_size=5, max_size=5)
        result = allocate(make_students(5), [rule])
        self.assertEqual(result.status, 'ok')
        self.assertEqual(list(result.teams), ['Team 1'])
        self.assertEqual([student.id for student in result.teams['Team 1']], [1, 2, 3, 4, 5])
        self.assertEqual(result.violations, [])
        self.assertEqual(result.message, 'Allocated 5 students into 1 teams.')

    def test_policy_without_a_team_size_rule_is_infeasible(self):
        result = allocate(make_students(8), [FakeGenderRule()])
        self.assertEqual(result.status, 'infeasible')
        self.assertEqual(result.message,
                         'The policy has no team size rule, so the number of teams is unknown.')
        assert_empty_non_ok_result(self, result)

    def test_duplicate_student_id_raises_value_error(self):
        students = make_students(7) + make_students(1, start=1)
        with self.assertRaises(ValueError) as context:
            allocate(students, [self.size_rule])
        self.assertEqual(str(context.exception), 'Each student may appear only once.')

    def test_hard_4_5_rule_plus_soft_4_4_rule_shapes_teams_by_the_hard_rule(self):
        soft_size_rule = TeamSizeRule(min_size=4, max_size=4, hard=False, priority=2)
        students = make_students(9)
        rules = [self.size_rule, soft_size_rule]
        result = allocate(students, rules)
        self.assertEqual(result.status, 'ok')
        for name, members in result.teams.items():
            self.assertTrue(4 <= len(members) <= 5, f'{name} has {len(members)} members.')
        [violation] = result.violations
        self.assertEqual(violation.rule, 'team_size')
        self.assertFalse(violation.hard)
        self.assertEqual(violation.amount, 1)
        self.assertEqual(len(result.teams[violation.team]), 5)
        self.assertEqual(result.message,
                         'Allocated 9 students into 2 teams. 1 preference(s) could not be met.')
