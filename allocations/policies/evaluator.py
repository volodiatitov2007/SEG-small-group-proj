"""Evaluate a set of rules against any allocation."""
from math import ceil

from .base import Rule, Teams, Violation

# Soft-rule weights by priority: one high-priority violation outweighs many low ones.
WEIGHT = {1: 100, 2: 10, 3: 1}


def evaluate(rules: list[Rule], teams: Teams) -> list[Violation]:
    """Return every violation, hard ones first, then by priority and team name."""
    found = [v for rule in rules for v in rule.check_allocation(teams)]
    return sorted(found, key=lambda v: (not v.hard, v.priority, v.team or ""))


def is_valid(rules: list[Rule], teams: Teams) -> bool:
    """An allocation is valid when it breaks no hard rule."""
    return not any(v.hard for v in evaluate(rules, teams))


def soft_cost(rules: list[Rule], teams: Teams) -> float:
    """Weighted total of soft violations; lower is better. For comparing allocations."""
    return sum(v.amount * WEIGHT[v.priority] for v in evaluate(rules, teams) if not v.hard)


def team_size_problem(student_count: int, min_size: int, max_size: int) -> str | None:
    """Explain why the students provably cannot be split into teams of this size.

    Returns None when a split exists. With k teams, k * min_size <= n <= k * max_size,
    so a split exists exactly when ceil(n / max_size) <= floor(n / min_size).
    """
    if min_size < 1 or min_size > max_size:
        return f"Team sizes {min_size}-{max_size} are not a valid range."
    if student_count <= 0:
        return "There are no students to allocate."
    if ceil(student_count / max_size) <= student_count // min_size:
        return None
    return f"{student_count} students cannot be split into teams of {min_size}-{max_size}."


def team_size_feasible(student_count: int, min_size: int, max_size: int) -> bool:
    """Return True when the students can be split into teams of this size, else False."""
    return team_size_problem(student_count, min_size, max_size) is None
