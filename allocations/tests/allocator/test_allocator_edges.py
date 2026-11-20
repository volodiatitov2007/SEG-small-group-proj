from django.test import TestCase

from allocations.allocator import INFEASIBLE, TIMEOUT, _greedy_start, _team_counts, allocate
from allocations.policies import TeamSizeRule
from allocations.policies.evaluator import evaluate, is_valid
from allocations.tests.allocator.helpers import (
    AlwaysBrokenHardRule, CountingRule, FakeGenderRule, FirstTeamSizePenaltyRule,
    RecordingRule, assert_empty_non_ok_result, assert_ok_invariants, make_students,
)


class SoftOnlySizeRuleTestCase(TestCase):
    """Tests that a soft team size rule with no hard one still shapes the teams."""

    def setUp(self):
        self.rule = TeamSizeRule(min_size=4, max_size=5, hard=False, priority=2)

    def test_soft_only_size_rule_shapes_teams_of_nine_students(self):
        result = allocate(make_students(9), [self.rule])
        self.assertEqual(result.status, 'ok')
        self.assertEqual([len(members) for members in result.teams.values()], [5, 4])
        self.assertEqual(result.violations, [])
        self.assertEqual(result.message, 'Allocated 9 students into 2 teams.')

    def test_soft_only_size_rule_still_allocates_when_no_split_fits_the_range(self):
        rule = TeamSizeRule(min_size=4, max_size=4, hard=False, priority=2)
        result = allocate(make_students(9), [rule])
        self.assertEqual(result.status, 'ok')
        self.assertEqual([len(members) for members in result.teams.values()], [5, 4])
        [violation] = result.violations
        self.assertEqual(violation.rule, 'team_size')
        self.assertEqual(violation.team, 'Team 1')
        self.assertEqual(violation.message, 'Team 1 has 5 students; the maximum is 4.')
        self.assertFalse(violation.hard)

    def test_seven_students_with_a_soft_only_size_rule_allocate_into_teams_of_4_and_3(self):
        result = allocate(make_students(7), [self.rule])
        self.assertEqual(result.status, 'ok')
        self.assertEqual([len(members) for members in result.teams.values()], [4, 3])
        [violation] = result.violations
        self.assertEqual(violation.rule, 'team_size')
        self.assertEqual(violation.team, 'Team 2')
        self.assertEqual(violation.message, 'Team 2 has 3 students; the minimum is 4.')
        self.assertFalse(violation.hard)

    def test_eleven_students_with_a_soft_only_size_rule_allocate_with_soft_violations(self):
        students = make_students(11)
        result = allocate(students, [self.rule])
        self.assertEqual(result.status, 'ok')
        allocated_ids = sorted(student.id for members in result.teams.values()
                               for student in members)
        self.assertEqual(allocated_ids, sorted(student.id for student in students))
        self.assertEqual(result.violations, evaluate([self.rule], result.teams))

    def test_a_soft_only_size_rule_with_no_students_is_infeasible(self):
        result = allocate([], [self.rule])
        self.assertEqual(result.status, 'infeasible')
        self.assertEqual(result.message, 'There are no students to allocate.')
        assert_empty_non_ok_result(self, result)


class TeamCountTestCase(TestCase):
    """Tests how many teams the allocator picks for a cohort and size range."""

    def test_feasible_ranges_pick_the_fewest_teams_that_fit_the_maximum(self):
        for student_count, team_count in ((8, 2), (9, 2), (300, 60)):
            with self.subTest(student_count=student_count):
                self.assertEqual(_team_counts(student_count, 4, 5)[0], team_count)

    def test_impossible_ranges_pick_the_count_that_breaks_the_range_least(self):
        # 11 = 6+5 and 11 = 4+4+3 tie on the gap, so the fewest teams wins.
        for student_count, team_count in ((7, 2), (11, 2), (3, 1), (1, 1)):
            with self.subTest(student_count=student_count):
                self.assertEqual(_team_counts(student_count, 4, 5)[0], team_count)


class TwoHardSizeRulesTestCase(TestCase):
    """Tests which of several hard team size rules the allocator obeys."""

    def test_the_first_hard_size_rule_gates_feasibility(self):
        first, second = TeamSizeRule(min_size=4, max_size=5), TeamSizeRule(min_size=3, max_size=4)
        result = allocate(make_students(11), [first, second])
        self.assertEqual(result.status, INFEASIBLE)
        self.assertEqual(result.message, '11 students cannot be split into teams of 4-5.')

    def test_a_second_unsatisfiable_hard_size_rule_times_out(self):
        first, second = TeamSizeRule(min_size=4, max_size=5), TeamSizeRule(min_size=4, max_size=4)
        rules = [first, second]
        result = allocate(make_students(9), rules, max_steps=100)
        self.assertEqual(result.status, TIMEOUT)
        self.assertEqual(
            result.message,
            'No allocation meeting every hard rule was found in time. '
            'This is not proof that none exists.')
        self.assertEqual(result.teams, {})
        self.assertEqual(result.violations, [])


class MaxStepsCountingTestCase(TestCase):
    """Tests that max_steps bounds the number of rule checks exactly."""

    def test_max_steps_bounds_rule_checks_to_two_scorings_per_step(self):
        counting = CountingRule()
        rules = [TeamSizeRule(min_size=4, max_size=5), AlwaysBrokenHardRule(), counting]
        result = allocate(make_students(12), rules, max_steps=10, time_limit=30)
        self.assertEqual(result.status, TIMEOUT)
        # 3 initial team scorings (evaluate + soft_cost) + 4 per step (two teams,
        # each scored by evaluate and soft_cost) + scoring the finished count (3 x 2)
        # + the final evaluate and is_valid.
        self.assertEqual(counting.calls, 3 * 2 + 4 * 10 + 3 * 2 + 3 + 3)

    def test_patience_stop_bounds_rule_checks_when_no_improvement_is_possible(self):
        counting = CountingRule()
        rules = [TeamSizeRule(min_size=4, max_size=5), AlwaysBrokenHardRule(), counting]
        result = allocate(make_students(12), rules, time_limit=60)
        self.assertEqual(result.status, TIMEOUT)
        # patience = max(2000, 50 * 12) idle steps with no strict improvement among
        # them; same per-step and final-scoring costs as the max_steps test above.
        self.assertEqual(counting.calls, 3 * 2 + 4 * 2000 + 3 * 2 + 3 + 3)

    def test_search_is_skipped_entirely_for_a_single_team(self):
        counting = CountingRule()
        rules = [TeamSizeRule(min_size=5, max_size=5), AlwaysBrokenHardRule(), counting]
        result = allocate(make_students(5), rules, max_steps=50, time_limit=30)
        self.assertEqual(result.status, TIMEOUT)
        # Only scoring the single team count and the final evaluate and is_valid run;
        # the search loop never scores a team.
        self.assertEqual(counting.calls, 2 + 2)

    def test_search_stops_immediately_when_every_team_already_scores_zero(self):
        counting = CountingRule()
        rules = [TeamSizeRule(min_size=4, max_size=5), counting]
        result = allocate(make_students(12), rules, max_steps=100)
        self.assertEqual(result.status, 'ok')
        # Initial scoring (3 teams x 2), scoring the finished count (3 x 2) plus the final
        # evaluate and is_valid (3 + 3); not a single search step runs.
        self.assertEqual(counting.calls, 3 * 2 + 3 * 2 + 3 + 3)


class MoveStepTestCase(TestCase):
    """Tests that the search uses moving steps, not only swaps."""

    def test_moving_a_student_out_of_team_1_fixes_the_last_violation(self):
        students = make_students(9)
        rules = [TeamSizeRule(min_size=4, max_size=5), FirstTeamSizePenaltyRule(limit=4)]
        result = allocate(students, rules, seed=0, max_steps=5000, time_limit=5)
        # Swaps cannot change team sizes, so reaching [4, 5] proves a move was taken.
        self.assertEqual([len(members) for members in result.teams.values()], [4, 5])
        assert_ok_invariants(self, result, students, rules)
        self.assertEqual(result.violations, [])
        self.assertEqual(result.message, 'Allocated 9 students into 2 teams.')


class PrepareOrderingTestCase(TestCase):
    """Tests that prepare() only runs once feasibility has been established."""

    def test_prepare_is_not_called_when_the_cohort_is_infeasible(self):
        recording = RecordingRule()
        result = allocate(make_students(7), [TeamSizeRule(min_size=4, max_size=5), recording])
        self.assertEqual(result.status, INFEASIBLE)
        self.assertEqual(recording.prepare_calls, [])

    def test_prepare_is_not_called_when_the_policy_has_no_team_size_rule(self):
        recording = RecordingRule()
        result = allocate(make_students(8), [recording])
        self.assertEqual(result.status, INFEASIBLE)
        self.assertEqual(recording.prepare_calls, [])


class ResultIdentityTestCase(TestCase):
    """Tests that result teams hold the very objects that were passed in."""

    def test_team_members_are_the_same_student_objects_that_were_passed_in(self):
        students = make_students(9)
        result = allocate(students, [TeamSizeRule(min_size=4, max_size=5)])
        members = [student for team in result.teams.values() for student in team]
        self.assertEqual(len(members), 9)
        for member in members:
            self.assertTrue(any(member is student for student in students))


class OkMessagePreferencesTestCase(TestCase):
    """Tests the ok message wording for more than one unmet preference."""

    def test_ok_message_counts_two_unmet_preferences(self):
        rules = [
            TeamSizeRule(min_size=4, max_size=5),
            TeamSizeRule(min_size=4, max_size=4, hard=False, priority=2),
            TeamSizeRule(min_size=4, max_size=4, hard=False, priority=3),
        ]
        result = allocate(make_students(9), rules)
        self.assertEqual(result.status, 'ok')
        self.assertEqual(len(result.violations), 2)
        self.assertEqual(result.message,
                         'Allocated 9 students into 2 teams. 2 preference(s) could not be met.')


class SeedVariationTestCase(TestCase):
    """Tests that different seeds can settle on different teams of equal cost."""

    def test_two_seeds_give_different_teams_on_a_cohort_with_many_equal_choices(self):
        students = make_students(12, genders=[1, 1, 1, 2, 1, 1, 1, 2, 1, 1, 1, 2],
                                 c_scores=[5] * 12)
        rules = [TeamSizeRule(min_size=4, max_size=5), FakeGenderRule()]
        first = allocate(students, rules, seed=0)
        second = allocate(students, rules, seed=1)
        first_ids = [[student.id for student in members] for members in first.teams.values()]
        second_ids = [[student.id for student in members] for members in second.teams.values()]
        self.assertEqual(first.status, 'ok')
        self.assertEqual(second.status, 'ok')
        self.assertTrue(is_valid(rules, first.teams))
        self.assertTrue(is_valid(rules, second.teams))
        self.assertNotEqual(first_ids, second_ids)


class GreedyNoneScoreOrderingTestCase(TestCase):
    """Tests that the greedy start orders students without a c-score last."""

    def test_students_without_c_scores_are_cut_into_the_last_blocks(self):
        students = make_students(4, c_scores=[1, None, 2, None])
        result = allocate(students, [TeamSizeRule(min_size=2, max_size=2)], max_steps=0)
        greedy = _greedy_start(students, 2)
        self.assertEqual([[student.id for student in members] for members in result.teams.values()],
                         [[student.id for student in members] for members in greedy.values()])
        self.assertEqual([[student.id for student in members] for members in result.teams.values()],
                         [[1, 3], [2, 4]])
