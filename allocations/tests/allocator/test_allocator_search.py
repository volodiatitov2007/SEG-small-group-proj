from django.test import TestCase

from allocations.allocator import TIMEOUT, _greedy_start, allocate
from allocations.policies import TeamSizeRule
from allocations.policies.evaluator import soft_cost
from allocations.tests.allocator.helpers import (
    AlwaysBrokenHardRule, FakeAttainmentSpreadRule, KeepApartRule, RecordingRule, SlowRule,
    assert_empty_non_ok_result, assert_ok_invariants, make_students,
)


class PrepareCalledOnceTestCase(TestCase):
    """Tests that every rule's prepare() runs exactly once with the whole cohort."""

    def setUp(self):
        self.size_rule = TeamSizeRule(min_size=4, max_size=5)
        self.students = make_students(12)

    def test_prepare_is_called_exactly_once_per_rule_with_all_students(self):
        first, second = RecordingRule(), RecordingRule()
        allocate(self.students, [self.size_rule, first, second])
        expected_ids = [student.id for student in self.students]
        self.assertEqual(first.prepare_calls, [expected_ids])
        self.assertEqual(second.prepare_calls, [expected_ids])


class ImpossibleHardRuleTestCase(TestCase):
    """Tests that a never-satisfiable hard rule yields a timeout, never 'infeasible'."""

    def setUp(self):
        self.rules = [TeamSizeRule(min_size=4, max_size=5), AlwaysBrokenHardRule()]
        self.students = make_students(12)

    def test_never_satisfiable_hard_rule_times_out_without_claiming_proof(self):
        result = allocate(self.students, self.rules, max_steps=100)
        self.assertEqual(result.status, TIMEOUT)
        self.assertEqual(
            result.message,
            'No allocation meeting every hard rule was found in time. '
            'This is not proof that none exists.')
        assert_empty_non_ok_result(self, result)


class SatisfiableHardRuleTestCase(TestCase):
    """Tests that a hard rule some allocation can satisfy ends 'ok' with it met."""

    def setUp(self):
        self.size_rule = TeamSizeRule(min_size=4, max_size=5)

    def test_satisfiable_keep_apart_rule_ends_ok_with_the_pair_separated(self):
        students = make_students(12, c_scores=[1, 2, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19])
        rules = [self.size_rule, KeepApartRule(first_id=1, second_id=2)]
        result = allocate(students, rules, seed=3)
        self.assertEqual(result.status, 'ok')
        for members in result.teams.values():
            ids = {student.id for student in members}
            self.assertNotEqual(ids & {1, 2}, {1, 2})
        assert_ok_invariants(self, result, students, rules)


class SoftImprovementTestCase(TestCase):
    """Tests that local search improves on or matches the greedy start's soft cost."""

    def setUp(self):
        self.size_rule = TeamSizeRule(min_size=4, max_size=5)

    def test_result_soft_cost_is_at_most_the_greedy_start_soft_cost(self):
        students = make_students(12, c_scores=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
        rules = [self.size_rule, FakeAttainmentSpreadRule(max_spread=2)]
        greedy = _greedy_start(students, 3)
        self.assertEqual(soft_cost(rules, greedy), 3)
        result = allocate(students, rules, seed=5)
        self.assertEqual(result.status, 'ok')
        self.assertLessEqual(soft_cost(rules, result.teams), 3)

    def test_search_reaches_zero_soft_cost_on_an_easy_case(self):
        students = make_students(9, c_scores=[1, 1, 1, 1, 2, 2, 2, 2, 2])
        rules = [self.size_rule, FakeAttainmentSpreadRule(max_spread=0)]
        greedy = _greedy_start(students, 2)
        self.assertEqual(soft_cost(rules, greedy), 1)
        result = allocate(students, rules, seed=0, max_steps=5000, time_limit=5)
        self.assertEqual(result.status, 'ok')
        self.assertEqual(soft_cost(rules, result.teams), 0)
        self.assertEqual(result.violations, [])


class DeterminismTestCase(TestCase):
    """Tests that the same seed and max_steps reproduce the same teams."""

    def setUp(self):
        self.students = make_students(
            40,
            genders=[1, 2, 3, 0, 1, 2, 3, 0] * 5,
            c_scores=[(index * 7) % 21 for index in range(40)],
        )
        self.rules = [TeamSizeRule(min_size=4, max_size=5), FakeAttainmentSpreadRule(max_spread=4)]

    def ids(self, result):
        return [[student.id for student in members] for members in result.teams.values()]

    def test_same_seed_and_max_steps_give_identical_teams_on_repeated_runs(self):
        first = allocate(self.students, self.rules, seed=123, max_steps=250)
        second = allocate(self.students, self.rules, seed=123, max_steps=250)
        self.assertEqual(first.status, 'ok')
        self.assertEqual(self.ids(first), self.ids(second))


class GreedyFallbackTestCase(TestCase):
    """Tests the zero-step boundary of the search."""

    def setUp(self):
        self.students = make_students(12, c_scores=[12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1])
        self.rules = [TeamSizeRule(min_size=4, max_size=5)]

    def test_max_steps_of_zero_still_returns_a_valid_greedy_allocation(self):
        result = allocate(self.students, self.rules, max_steps=0)
        assert_ok_invariants(self, result, self.students, self.rules)
        greedy_ids = [[student.id for student in members]
                      for members in _greedy_start(self.students, 3).values()]
        self.assertEqual([[student.id for student in members]
                          for members in result.teams.values()], greedy_ids)


class TimeLimitTestCase(TestCase):
    """Tests that the deadline is honoured even when rules are slow."""

    def setUp(self):
        self.size_rule = TeamSizeRule(min_size=4, max_size=5)

    def test_slow_rule_with_short_time_limit_finishes_within_the_limit_plus_slack(self):
        students = make_students(10)
        result = allocate(students, [self.size_rule, SlowRule(delay=0.01)], time_limit=0.3)
        self.assertLess(result.duration_seconds, 0.3 + 1.5)
        self.assertEqual(result.status, 'ok')
        assert_ok_invariants(self, result, students, [self.size_rule])

    def test_deadline_stops_the_search_when_scores_are_never_zero(self):
        # The old slow-rule test never reached the deadline: a no-op slow rule scores
        # (0, 0) everywhere, so the search early-returns before any timed step.
        students = make_students(12)
        rules = [self.size_rule, AlwaysBrokenHardRule(), SlowRule(delay=0.01)]
        result = allocate(students, rules, time_limit=0.3)
        self.assertEqual(result.status, TIMEOUT)
        self.assertGreaterEqual(result.duration_seconds, 0.3)
        self.assertLess(result.duration_seconds, 0.3 + 1.5)
        assert_empty_non_ok_result(self, result)


class InputImmutabilityTestCase(TestCase):
    """Tests that allocate() leaves its input untouched."""

    def setUp(self):
        self.students = make_students(12, c_scores=[9, 1, 8, 2, 7, 3, 6, 4, 5, 5, 4, 6])
        self.rules = [TeamSizeRule(min_size=4, max_size=5)]

    def test_input_list_order_is_unchanged_after_allocation(self):
        ids_before = [student.id for student in self.students]
        allocate(self.students, self.rules, seed=1, max_steps=100)
        self.assertEqual([student.id for student in self.students], ids_before)
