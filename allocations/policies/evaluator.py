"""Evaluate a set of rules against any allocation."""
import re
from math import ceil

from .base import Rule, StudentView, Teams, Violation

# Soft-rule weights by priority: one high-priority violation outweighs many low ones.
WEIGHT = {1: 100, 2: 10, 3: 1}


MEMBERSHIP_KEY = 'membership'


def team_order(name: str | None) -> list:
    """Sort key that puts 'Team 2' before 'Team 10' by comparing the numbers in a name."""
    parts = re.split(r'(\d+)', name or '')
    return [int(part) if part.isdigit() else part for part in parts]


def evaluate(rules: list[Rule], teams: Teams) -> list[Violation]:
    """Return every violation, hard ones first, then by priority and team name."""
    found = [v for rule in rules for v in rule.check_allocation(teams)]
    return sorted(found, key=lambda v: (not v.hard, v.priority, team_order(v.team)))


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
        return f'Team sizes {min_size}-{max_size} are not a valid range.'
    if student_count <= 0:
        return 'There are no students to allocate.'
    if ceil(student_count / max_size) <= student_count // min_size:
        return None
    return f'{student_count} students cannot be split into teams of {min_size}-{max_size}.'


def team_size_feasible(student_count: int, min_size: int, max_size: int) -> bool:
    """Return True when the students can be split into teams of this size, else False."""
    return team_size_problem(student_count, min_size, max_size) is None


def check_membership(students: list[StudentView], teams: Teams) -> list[Violation]:
    """Report every student who is not in exactly one team, and any member not in the cohort.

    An empty list means the allocation places each student of the cohort exactly once.
    """
    cohort_ids = {student.id for student in students}
    placed: dict[int, list[str]] = {}
    found = []
    for team in sorted(teams, key=team_order):
        for member in teams[team]:
            placed.setdefault(member.id, []).append(team)
            if member.id not in cohort_ids:
                found.append(_membership_violation(
                    team, f'{team} contains {member.name}, who is not in the cohort.'))
    for student in students:
        in_teams = placed.get(student.id, [])
        if not in_teams:
            found.append(_membership_violation(None, f'{student.name} is not in any team.'))
        elif len(in_teams) > 1:
            names = ', '.join(in_teams)
            found.append(_membership_violation(
                None, f'{student.name} is in more than one team ({names}).'))
    return found


def _membership_violation(team: str | None, message: str) -> Violation:
    return Violation(MEMBERSHIP_KEY, True, 1, team, message)
