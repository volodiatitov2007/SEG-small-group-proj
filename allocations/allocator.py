"""Split a cohort into teams that meet a policy's rules.

Plain Python with no Django imports. All rule logic lives in allocations.policies;
this module only calls evaluate, is_valid, soft_cost and team_size_feasible.
"""
import random
import time
from dataclasses import dataclass, field
from math import ceil

from .policies.base import Rule, StudentView, Teams
from .policies.evaluator import evaluate, is_valid, soft_cost, team_size_feasible, team_size_problem

OK = 'ok'
INFEASIBLE = 'infeasible'
TIMEOUT = 'timeout'

SIZE_RULE_KEY = 'team_size'


@dataclass
class AllocationResult:
    """The outcome of one allocation attempt."""

    status: str
    teams: Teams = field(default_factory=dict)
    violations: list = field(default_factory=list)
    message: str = ''
    duration_seconds: float = 0.0


def allocate(students: list[StudentView], rules: list[Rule], time_limit: float = 15.0,
             seed: int = 0, max_steps: int | None = None) -> AllocationResult:
    """Return the best allocation found within the time limit, or why there is none.

    Same seed and max_steps give the same teams; without max_steps the deadline may cut the search at a different point.
    """
    started = time.monotonic()
    deadline = started + time_limit

    def finish(status, message, teams=None, violations=None):
        return AllocationResult(status, teams or {}, violations or [], message, time.monotonic() - started)

    ids = [student.id for student in students]
    if len(set(ids)) != len(ids):
        raise ValueError('Each student may appear only once.')
    size_rules = sorted((rule for rule in rules if rule.key == SIZE_RULE_KEY), key=lambda rule: not rule.hard)
    size_rule = size_rules[0] if size_rules else None  # a hard size rule shapes the teams before a soft one
    if size_rule is None:
        return finish(INFEASIBLE, 'The policy has no team size rule, so the number of teams is unknown.')
    min_size, max_size = size_rule.min_size, size_rule.max_size
    if not team_size_feasible(len(students), min_size, max_size):
        return finish(INFEASIBLE, team_size_problem(len(students), min_size, max_size))

    for rule in rules:
        rule.prepare(list(students))
    teams = _greedy_start(students, ceil(len(students) / max_size))
    _local_search(teams, rules, min_size, max_size, deadline, random.Random(seed), max_steps)

    violations = evaluate(rules, teams)
    if not is_valid(rules, teams):
        return finish(TIMEOUT, 'No allocation meeting every hard rule was found in time. '
                               'This is not proof that none exists.')
    message = f'Allocated {len(students)} students into {len(teams)} teams.'
    if violations:
        message += f' {len(violations)} preference(s) could not be met.'
    return finish(OK, message, teams, violations)


def _greedy_start(students: list[StudentView], team_count: int) -> Teams:
    """Sort by c-score and cut into consecutive blocks whose sizes differ by at most one."""
    ordered = sorted(students, key=lambda s: (s.c_score is None, s.c_score or 0, s.id))
    base, extra = divmod(len(ordered), team_count)
    teams, start = {}, 0
    for number in range(1, team_count + 1):
        size = base + (1 if number <= extra else 0)
        teams[f'Team {number}'] = ordered[start:start + size]
        start += size
    return teams


def _score(rules: list[Rule], teams: Teams) -> tuple[float, float]:
    """Score some teams as (total hard violation amount, soft cost); lower is better."""
    hard = sum(v.amount for v in evaluate(rules, teams) if v.hard)
    return hard, soft_cost(rules, teams)


def _local_search(teams: Teams, rules: list[Rule], min_size: int, max_size: int,
                  deadline: float, rng: random.Random, max_steps: int | None) -> None:
    """Improve teams in place with random swaps and moves, rescoring only the two teams touched."""
    names = list(teams)
    if len(names) < 2:
        return
    scores = {name: _score(rules, {name: teams[name]}) for name in names}
    patience = max(2000, 50 * sum(len(members) for members in teams.values()))
    steps = idle = 0
    while time.monotonic() < deadline and idle < patience and (max_steps is None or steps < max_steps):
        if all(score == (0, 0) for score in scores.values()):
            return
        steps += 1
        idle += 1
        a, b = rng.sample(names, 2)
        old_a, old_b = teams[a], teams[b]
        if rng.random() < 0.5 and len(old_a) > min_size and len(old_b) < max_size:
            i = rng.randrange(len(old_a))
            new_a, new_b = old_a[:i] + old_a[i + 1:], old_b + [old_a[i]]
        else:
            i, j = rng.randrange(len(old_a)), rng.randrange(len(old_b))
            new_a = old_a[:i] + [old_b[j]] + old_a[i + 1:]
            new_b = old_b[:j] + [old_a[i]] + old_b[j + 1:]
        score_a, score_b = _score(rules, {a: new_a}), _score(rules, {b: new_b})
        old_total = _add(scores[a], scores[b])
        new_total = _add(score_a, score_b)
        if new_total <= old_total:  # sideways steps help cross flat ground
            if new_total < old_total:
                idle = 0
            teams[a], teams[b] = new_a, new_b
            scores[a], scores[b] = score_a, score_b


def _add(first: tuple[float, float], second: tuple[float, float]) -> tuple[float, float]:
    return first[0] + second[0], first[1] + second[1]
