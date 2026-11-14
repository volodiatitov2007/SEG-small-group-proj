"""Core types shared by every allocation rule.

Nothing in this package imports Django or a solver, so the allocator, the
results pages and the tests can all call the rules directly.
"""
from dataclasses import dataclass, field

PRIORITIES = (1, 2, 3)  # 1 = high, 2 = medium, 3 = low


@dataclass(frozen=True)
class StudentView:
    """The read-only view of a student that rules work with."""

    id: int
    name: str
    gender: int | None = None      # 0 = not provided, None = column absent
    ethnicity: int | None = None
    c_score: int | None = None
    extra: dict = field(default_factory=dict, hash=False, compare=False)


@dataclass(frozen=True)
class Violation:
    """One unmet rule, explained in plain language."""

    rule: str                # the rule's key, e.g. "team_size"
    hard: bool
    priority: int            # 1 = most important
    team: str | None         # team name, or None for whole-allocation problems
    message: str             # shown to staff exactly as written
    amount: float = 1.0      # how bad; used for scoring only, never shown alone


Teams = dict[str, list[StudentView]]


class Rule:
    """Base class for an allocation rule that can be hard or soft."""

    key = "base"

    def __init__(self, hard: bool, priority: int = 1):
        if priority not in PRIORITIES:
            raise ValueError(f"Priority must be one of {PRIORITIES}, not {priority}.")
        self.hard = hard
        self.priority = priority

    def prepare(self, students: list[StudentView]) -> None:
        """Record any whole-cohort facts this rule needs. Call once, before checking.

        Rules that only look inside a team need nothing, so the default does nothing.
        """

    def check_team(self, name: str, members: list[StudentView]) -> list[Violation]:
        """Return the violations of this rule within one team, given only that team."""
        raise NotImplementedError

    def check_allocation(self, teams: Teams) -> list[Violation]:
        """Return the violations of this rule across a whole allocation."""
        return [v for name, members in teams.items() for v in self.check_team(name, members)]

    def params(self) -> dict:
        """Return the rule-specific settings, for saving as JSON."""
        return {}

    def to_dict(self) -> dict:
        return {"key": self.key, "hard": self.hard, "priority": self.priority, **self.params()}

    @classmethod
    def from_dict(cls, data: dict) -> "Rule":
        settings = {name: value for name, value in data.items() if name != "key"}
        return cls(**settings)

    def violation(self, team: str | None, message: str, amount: float = 1.0) -> Violation:
        """Build a violation of this rule with its hard/soft flag and priority."""
        return Violation(self.key, self.hard, self.priority, team, message, amount)

    def __eq__(self, other):
        return type(self) is type(other) and self.to_dict() == other.to_dict()

    def __repr__(self):
        return f"{type(self).__name__}({self.to_dict()})"
