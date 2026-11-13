"""Allocation policies: rule types, violations and the evaluator."""
from .base import Rule, StudentView, Violation
from .rules import TeamSizeRule

__all__ = ["RULES", "Rule", "StudentView", "TeamSizeRule", "Violation", "rule_from_dict"]

RULES = {rule.key: rule for rule in (TeamSizeRule,)}


def rule_from_dict(data: dict) -> Rule:
    """Rebuild a rule from its saved JSON form."""
    return RULES[data["key"]].from_dict(data)
