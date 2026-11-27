"""Allocation policies: rule types, violations and the evaluator."""
from .adapters import student_view
from .base import Rule, StudentView, Violation
from .rules import GenderRule, TeamSizeRule

__all__ = [
    'RULES', 'GenderRule', 'Rule', 'StudentView', 'TeamSizeRule', 'Violation', 'describe_rules',
    'rule_from_dict', 'student_view',
]

RULES = {rule.key: rule for rule in (TeamSizeRule, GenderRule)}


def rule_from_dict(data: dict) -> Rule:
    """Rebuild a rule from its saved JSON form."""
    key = data.get('key')
    if key not in RULES:
        known = ', '.join(sorted(RULES))
        raise ValueError(f"Unknown rule '{key}'. Known rules: {known}.")
    return RULES[key].from_dict(data)


def describe_rules(rules_data: list) -> list[str]:
    """Return one line per saved rule for staff, naming any rule that cannot be read."""
    lines = []
    for data in rules_data:
        try:
            lines.append(rule_from_dict(data).describe())
        except (ValueError, TypeError, AttributeError):
            key = data.get('key') if isinstance(data, dict) else data
            lines.append(f"Unknown rule '{key}'")
    return lines
