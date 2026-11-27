"""The concrete allocation rules."""
from .base import Rule, StudentView, Violation


def _students(count: int) -> str:
    return '1 student' if count == 1 else f'{count} students'


class TeamSizeRule(Rule):
    """Every team has between min_size and max_size students (inclusive)."""

    key = 'team_size'

    def __init__(self, min_size: int, max_size: int, hard: bool = True, priority: int = 1):
        super().__init__(hard, priority)
        if min_size < 1:
            raise ValueError('The minimum team size must be at least 1.')
        if min_size > max_size:
            raise ValueError('The minimum team size cannot be larger than the maximum.')
        self.min_size = min_size
        self.max_size = max_size

    @property
    def label(self) -> str:
        return f'Team size {self.min_size}-{self.max_size}'

    def params(self) -> dict:
        return {'min_size': self.min_size, 'max_size': self.max_size}

    def check_team(self, name: str, members: list[StudentView]) -> list[Violation]:
        size = len(members)
        if size < self.min_size:
            return [self.violation(
                name,
                f'{name} has {_students(size)}; the minimum is {self.min_size}.',
                self.min_size - size,
            )]
        if size > self.max_size:
            return [self.violation(
                name,
                f'{name} has {_students(size)}; the maximum is {self.max_size}.',
                size - self.max_size,
            )]
        return []


WOMAN, MAN, OTHER = 1, 2, 3
GENDER_NAMES = {WOMAN: 'woman', MAN: 'man', OTHER: 'other/non-binary student'}


class GenderRule(Rule):
    """No student is the only one of their disclosed gender in a team.

    Women and men (codes 1 and 2) should have at least one team mate of the same gender.
    Where that is impossible, because the student is other/non-binary (code 3) or the only
    one of their gender in the cohort, the team should be gender-diverse instead: it should
    hold more than one disclosed gender. Gender 0 (not provided) and None (no gender column)
    are unknown: those students are skipped, and never count as company for anyone.
    """

    key = 'gender'
    label = 'Gender representation'
    PAIRED_GENDERS = (WOMAN, MAN)

    def __init__(self, hard: bool = False, priority: int = 1):
        super().__init__(hard, priority)
        self._cohort_counts = None  # set by prepare(); None means the cohort is unknown

    def prepare(self, students: list[StudentView]) -> None:
        """Count the students of each disclosed gender in the whole cohort."""
        counts = {}
        for student in students:
            if student.gender:
                counts[student.gender] = counts.get(student.gender, 0) + 1
        self._cohort_counts = counts

    def check_team(self, name: str, members: list[StudentView]) -> list[Violation]:
        by_gender = {}
        for member in members:
            if member.gender:
                by_gender.setdefault(member.gender, []).append(member)
        diverse = len(by_gender) > 1
        problems = []
        for gender, students in sorted(by_gender.items()):
            if len(students) > 1:
                continue
            gender_name = GENDER_NAMES.get(gender, f'student of gender {gender}')
            student = students[0].name
            if self._can_be_paired(gender):
                problems.append(f'only one {gender_name} ({student})')
            elif not diverse:
                problems.append(f'only one {gender_name} ({student}) and no other disclosed gender')
        if not problems:
            return []
        return [self.violation(name, f'{name} has {" and ".join(problems)}.', len(problems))]

    def _can_be_paired(self, gender: int) -> bool:
        """Whether a lone student of this gender should have a team mate of the same gender."""
        if gender not in self.PAIRED_GENDERS:
            return False
        if self._cohort_counts is None:
            return True
        return self._cohort_counts.get(gender, 0) > 1
