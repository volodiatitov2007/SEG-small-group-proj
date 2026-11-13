"""The concrete allocation rules."""
from .base import Rule, StudentView, Violation


def _students(count: int) -> str:
    return "1 student" if count == 1 else f"{count} students"


class TeamSizeRule(Rule):
    """Every team has between min_size and max_size students (inclusive)."""

    key = "team_size"

    def __init__(self, min_size: int, max_size: int, hard: bool = True, priority: int = 1):
        super().__init__(hard, priority)
        if min_size < 1:
            raise ValueError("The minimum team size must be at least 1.")
        if min_size > max_size:
            raise ValueError("The minimum team size cannot be larger than the maximum.")
        self.min_size = min_size
        self.max_size = max_size

    def params(self) -> dict:
        return {"min_size": self.min_size, "max_size": self.max_size}

    def check_team(self, name: str, members: list[StudentView]) -> list[Violation]:
        size = len(members)
        if size < self.min_size:
            return [self.violation(
                name,
                f"{name} has {_students(size)}; the minimum is {self.min_size}.",
                self.min_size - size,
            )]
        if size > self.max_size:
            return [self.violation(
                name,
                f"{name} has {_students(size)}; the maximum is {self.max_size}.",
                size - self.max_size,
            )]
        return []
