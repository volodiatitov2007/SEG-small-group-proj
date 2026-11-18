"""Property-style tests: the same invariants checked on many seeded random cohorts."""
import random
from collections import Counter

from django.test import SimpleTestCase

from allocations.allocator import INFEASIBLE, OK
from allocations.policies.evaluator import is_valid
from allocations.tests.allocator.helpers import assert_empty_non_ok_result, assert_ok_invariants
from allocations.tests.factories import make_cohort, make_policy, run_allocation

SEEDS = range(30)
MIN_SIZE, MAX_SIZE = 4, 5
# Cohort sizes that cannot be split into teams of 4 to 5. From 12 students up, a split always exists.
IMPOSSIBLE_SIZES = [1, 2, 3, 6, 7, 11]


def can_split(n, min_size=MIN_SIZE, max_size=MAX_SIZE):
    """Independent check: is there a number of teams k with k*min <= n <= k*max?"""
    return any(k * min_size <= n <= k * max_size for k in range(1, n + 1))


def lone_members(teams):
    """Independently find every (team, gender) where exactly one disclosed student has that gender."""
    found = set()
    for name, members in teams.items():
        counts = Counter(s.gender for s in members if s.gender in (1, 2, 3))
        found.update((name, gender) for gender, count in counts.items() if count == 1)
    return found


class RandomCohortInvariantsTestCase(SimpleTestCase):
    """Run 30 random cohorts of 8 to 120 students. A failure message names its seed."""

    def cohorts(self):
        """Yield (seed, n, cohort) with n between 8 and 120; every seed always gives the same cohort."""
        for seed in SEEDS:
            n = random.Random(seed).randint(8, 120)
            yield seed, n, make_cohort(n, seed=seed)

    def test_every_student_is_in_exactly_one_team(self):
        policy = make_policy()
        for seed, n, cohort in self.cohorts():
            with self.subTest(seed=seed, n=n):
                result = run_allocation(cohort, policy, seed=seed)
                if not can_split(n):
                    continue
                ids = [s.id for members in result.teams.values() for s in members]
                self.assertEqual(len(ids), len(set(ids)), 'A student appears twice.')
                self.assertEqual(set(ids), {s.id for s in cohort}, 'A student is missing.')

    def test_a_split_that_exists_always_gives_ok_and_a_valid_allocation(self):
        policy = make_policy()
        for seed, n, cohort in self.cohorts():
            if not can_split(n):
                continue
            with self.subTest(seed=seed, n=n):
                result = run_allocation(cohort, policy, seed=seed)
                assert_ok_invariants(self, result, cohort, policy)

    def test_a_split_that_does_not_exist_is_reported_infeasible_with_no_teams(self):
        policy = make_policy()
        for seed in SEEDS:
            n = random.Random(seed).choice(IMPOSSIBLE_SIZES)
            with self.subTest(seed=seed, n=n):
                self.assertFalse(can_split(n))
                result = run_allocation(make_cohort(n, seed=seed), policy, seed=seed)
                self.assertEqual(result.status, INFEASIBLE)
                self.assertTrue(result.message)
                assert_empty_non_ok_result(self, result)

    def test_every_reported_gender_violation_is_real_and_none_is_missing(self):
        policy = make_policy(spread=False)
        for seed, n, cohort in self.cohorts():
            if not can_split(n):
                continue
            with self.subTest(seed=seed, n=n):
                result = run_allocation(cohort, policy, seed=seed)
                reported = Counter(v.team for v in result.violations if v.rule == 'fake_gender')
                expected = Counter(name for name, _ in lone_members(result.teams))
                self.assertEqual(reported, expected)

    def test_the_same_seed_gives_the_same_teams(self):
        policy = make_policy()
        cohort = make_cohort(60, seed=7)
        first = run_allocation(cohort, policy, seed=3)
        second = run_allocation(cohort, policy, seed=3)
        self.assertEqual({k: [s.id for s in v] for k, v in first.teams.items()},
                         {k: [s.id for s in v] for k, v in second.teams.items()})
        self.assertEqual(first.status, OK)
        self.assertTrue(is_valid(policy, first.teams))
