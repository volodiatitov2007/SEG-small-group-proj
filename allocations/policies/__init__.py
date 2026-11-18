"""Allocation policies: rule types, violations and the evaluator."""
from .adapters import student_view
from .base import Rule, StudentView, Violation
from .rules import TeamSizeRule

__all__ = [
    'RULES', 'Rule', 'StudentView', 'TeamSizeRule', 'Violation', 'rule_from_dict', 'student_view',
]

RULES = {rule.key: rule for rule in (TeamSizeRule,)}


def rule_from_dict(data: dict) -> Rule:
    """Rebuild a rule from its saved JSON form."""
    key = data.get('key')
    if key not in RULES:
        known = ', '.join(sorted(RULES))
        raise ValueError(f"Unknown rule '{key}'. Known rules: {known}.")
    return RULES[key].from_dict(data)
