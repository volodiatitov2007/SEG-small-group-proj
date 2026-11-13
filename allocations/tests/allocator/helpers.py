"""Shared builders, fake rules and invariant checks for the allocator tests."""
import time

from allocations.policies import Rule, StudentView
from allocations.policies.evaluator import evaluate, is_valid


def make_students(count, start=1, genders=None, c_scores=None):
    """Make `count` students with consecutive ids and deterministic attributes."""
    students = []
    for offset in range(count):
        attributes = {}
        if genders is not None:
            attributes['gender'] = genders[offset]
        if c_scores is not None:
            attributes['c_score'] = c_scores[offset]
        students.append(StudentView(id=start + offset, name=f'Student {start + offset}', **attributes))
    return students


class FakeGenderRule(Rule):
    """Soft rule: a team must not contain exactly one member of a disclosed gender 1, 2 or 3."""

    key = 'fake_gender'

    def __init__(self, priority=2):
        super().__init__(hard=False, priority=priority)

    def check_team(self, name, members):
        violations = []
        for gender in (1, 2, 3):
            if sum(1 for member in members if member.gender == gender) == 1:
                violations.append(self.violation(
                    name, f'{name} isolates its only gender-{gender} student.', 1))
        return violations


class FakeAttainmentSpreadRule(Rule):
    """Soft rule: a team's c-score spread must not exceed max_spread; None scores are excluded."""

    key = 'fake_spread'

    def __init__(self, max_spread, priority=3):
        super().__init__(hard=False, priority=priority)
        self.max_spread = max_spread

    def params(self):
        return {'max_spread': self.max_spread}

    def check_team(self, name, members):
        scores = [member.c_score for member in members if member.c_score is not None]
        if not scores:
            return []
        excess = max(scores) - min(scores) - self.max_spread
        if excess > 0:
            return [self.violation(
                name, f'{name} spreads c-scores by more than {self.max_spread}.', excess)]
        return []


class AlwaysBrokenHardRule(Rule):
    """Hard rule that no team can ever satisfy."""

    key = 'fake_impossible'

    def __init__(self):
        super().__init__(hard=True)

    def check_team(self, name, members):
        return [self.violation(name, f'{name} breaks a rule that cannot be met.', 1)]


class KeepApartRule(Rule):
    """Hard rule: two given students must never share a team."""

    key = 'fake_keep_apart'

    def __init__(self, first_id, second_id):
        super().__init__(hard=True)
        self.first_id = first_id
        self.second_id = second_id

    def check_team(self, name, members):
        ids = {member.id for member in members}
        if {self.first_id, self.second_id} <= ids:
            return [self.violation(name, 'These two students must not share a team.', 1)]
        return []


class RecordingRule(Rule):
    """Soft no-op rule that records the student ids of every prepare() call."""

    key = 'fake_recording'

    def __init__(self):
        super().__init__(hard=False)
        self.prepare_calls = []

    def prepare(self, students):
        self.prepare_calls.append([student.id for student in students])

    def check_team(self, name, members):
        return []


class CountingRule(Rule):
    """Soft no-op rule that counts its check_team calls, for pinning search effort."""

    key = 'fake_counting'

    def __init__(self):
        super().__init__(hard=False)
        self.calls = 0

    def check_team(self, name, members):
        self.calls += 1
        return []


class FirstTeamSizePenaltyRule(Rule):
    """Soft rule: only the team named 'Team 1' must not hold more than `limit` students.

    Swaps never change team sizes, so a violation here can only be repaired by moving
    a student out of 'Team 1', never by swapping two students.
    """

    key = 'fake_first_team_size'

    def __init__(self, limit, priority=2):
        super().__init__(hard=False, priority=priority)
        self.limit = limit

    def check_team(self, name, members):
        if name == 'Team 1' and len(members) > self.limit:
            return [self.violation(
                name, f'Team 1 holds more than {self.limit} students.', len(members) - self.limit)]
        return []


class SlowRule(Rule):
    """Soft no-op rule that sleeps in check_team to exercise the time limit."""

    key = 'fake_slow'

    def __init__(self, delay):
        super().__init__(hard=False)
        self.delay = delay

    def check_team(self, name, members):
        time.sleep(self.delay)
        return []


def assert_ok_invariants(test_case, result, students, rules):
    """Assert every invariant that must hold for a status-'ok' allocation result."""
    test_case.assertEqual(result.status, 'ok')
    allocated_ids = sorted(student.id for members in result.teams.values() for student in members)
    test_case.assertEqual(allocated_ids, sorted(student.id for student in students))
    test_case.assertEqual(sum(len(members) for members in result.teams.values()), len(students))
    size_rule = next(rule for rule in rules if rule.key == 'team_size' and rule.hard)
    for name, members in result.teams.items():
        test_case.assertTrue(size_rule.min_size <= len(members) <= size_rule.max_size,
                             f'{name} has {len(members)} members.')
    test_case.assertEqual(list(result.teams),
                          [f'Team {number}' for number in range(1, len(result.teams) + 1)])
    test_case.assertTrue(is_valid(rules, result.teams))
    test_case.assertEqual(result.violations, evaluate(rules, result.teams))
    test_case.assertFalse(any(violation.hard for violation in result.violations))
    test_case.assertGreaterEqual(result.duration_seconds, 0)


def assert_empty_non_ok_result(test_case, result):
    """Assert the shape every non-'ok' result must have."""
    test_case.assertEqual(result.teams, {})
    test_case.assertEqual(result.violations, [])
    test_case.assertGreaterEqual(result.duration_seconds, 0)
