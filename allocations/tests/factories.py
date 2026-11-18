"""Builders for the cross-feature invariant tests.

These make a cohort, a policy and an allocation in one line each, so a test can
focus on what it checks. Everything here is plain Python: no database is needed.
Randomness always comes from a seeded random.Random, so a failing test can be
re-run and gives exactly the same cohort.
"""
import random

from allocations.allocator import allocate
from allocations.policies import StudentView, TeamSizeRule
from allocations.tests.allocator.helpers import FakeAttainmentSpreadRule, FakeGenderRule

# Gender codes follow the brief: 1 Woman, 2 Man, 3 Other/Non-binary, 0 not provided.
GENDER_CODES = [1, 2, 3, 0]
GENDER_WEIGHTS = [45, 45, 3, 7]

# Pass MISSING for a column to give every student None, like a CSV without that column.
MISSING = object()


def _values(spec, n, make_one):
    """Return n values: a list is used as given, a single value is repeated, None means random."""
    if spec is MISSING:
        return [None] * n
    if spec is None:
        return [make_one() for _ in range(n)]
    if isinstance(spec, (list, tuple)):
        if len(spec) != n:
            raise ValueError(f'Expected {n} values but got {len(spec)}.')
        return list(spec)
    return [spec] * n


def make_cohort(n, seed=0, genders=None, c_scores=None, ethnicities=None):
    """Return n students (as StudentView objects) with ids 1..n.

    genders, c_scores and ethnicities can each be a list of n values, one value
    to repeat for everyone, MISSING for no value at all, or left out to get
    random but reproducible values.
    """
    rng = random.Random(seed)
    gender_values = _values(genders, n, lambda: rng.choices(GENDER_CODES, GENDER_WEIGHTS)[0])
    c_score_values = _values(c_scores, n, lambda: rng.randint(0, 100))
    ethnicity_values = _values(ethnicities, n, lambda: rng.randint(0, 5))
    return [
        StudentView(id=i + 1, name=f'Student {i + 1}', gender=gender_values[i],
                    ethnicity=ethnicity_values[i], c_score=c_score_values[i])
        for i in range(n)
    ]


def make_policy(min_size=4, max_size=5, hard=True, gender=True, spread=True):
    """Return a list of rules: team size, plus optional gender and attainment rules.

    The gender and attainment rules are the stand-ins from the allocator tests until
    the real ones are merged; swap them here and every invariant test uses the new ones.
    """
    rules = [TeamSizeRule(min_size=min_size, max_size=max_size, hard=hard)]
    if gender:
        rules.append(FakeGenderRule())
    if spread:
        rules.append(FakeAttainmentSpreadRule(max_spread=10))
    return rules


def run_allocation(cohort, policy, seed=0, max_steps=3000, time_limit=20.0):
    """Allocate the cohort under the policy and return the AllocationResult.

    max_steps makes the search stop after a fixed number of steps, so the same
    inputs always give the same teams and the tests are not affected by how fast
    the computer is. time_limit is only a safety net.
    """
    return allocate(cohort, policy, time_limit=time_limit, seed=seed, max_steps=max_steps)
