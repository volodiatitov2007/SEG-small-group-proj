"""Run an allocation for a cohort and save the outcome."""
from dataclasses import asdict

from django.db import transaction

from allocations.allocator import INFEASIBLE, allocate
from allocations.models import AllocationRun, Team, TeamMembership
from allocations.policies import rule_from_dict, student_view


def run_allocation(cohort, policy, time_limit=15.0, seed=0):
    """Allocate the cohort's students under the policy and save the run, whatever the outcome.

    The policy is an object with a rules list of rule dicts, or such a list itself.
    A policy that cannot be read is saved as an infeasible run instead of raising.
    """
    rules_data = getattr(policy, 'rules', policy)
    try:
        rules = [rule_from_dict(data) for data in rules_data]
    except (ValueError, TypeError) as error:
        return AllocationRun.objects.create(
            project=cohort.project,
            cohort=cohort,
            policy_snapshot={'rules': rules_data},
            status=INFEASIBLE,
            message=f'The policy is not valid, so nothing was allocated. {error}',
        )

    students = list(cohort.students.all())
    student_by_id = {student.id: student for student in students}
    result = allocate([student_view(student) for student in students], rules, time_limit=time_limit, seed=seed)

    # The search runs above, outside the transaction, so no database lock is held while it works.
    with transaction.atomic():
        run = AllocationRun.objects.create(
            project=cohort.project,
            cohort=cohort,
            policy_snapshot={'rules': [rule.to_dict() for rule in rules]},
            status=result.status,
            message=result.message,
            violations=[asdict(violation) for violation in result.violations],
            duration_seconds=result.duration_seconds,
        )
        for name, members in result.teams.items():
            team = Team.objects.create(run=run, name=name)
            TeamMembership.objects.bulk_create(
                TeamMembership(team=team, student=student_by_id[member.id]) for member in members
            )
    return run
