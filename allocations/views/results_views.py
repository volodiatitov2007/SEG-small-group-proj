import csv
import json
import re

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from allocations.models import AllocationRun, Project, TeamMembership


def _owned_run(user, run_id, **filters):
    return get_object_or_404(AllocationRun.objects.select_related('project', 'cohort'),
                             pk=run_id, project__owner=user, **filters)


def _natural_sort_key(value):
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part.casefold())
        for part in re.split(r'(\d+)', str(value))
    )


def _policy_lines(snapshot):
    if isinstance(snapshot, dict) and isinstance(snapshot.get('rules'), list):
        rules = snapshot['rules']
        metadata = {key: value for key, value in snapshot.items() if key != 'rules'}
    elif isinstance(snapshot, list):
        rules = snapshot
        metadata = {}
    elif isinstance(snapshot, dict):
        rules = None
        metadata = snapshot
    else:
        return [str(snapshot)] if snapshot else []

    lines = []
    if rules is not None:
        lines.extend(_policy_rule_line(rule) for rule in rules)
    lines.extend(
        f'{_humanize(key)}: {_policy_value(value)}'
        for key, value in metadata.items()
    )
    return lines


def _policy_rule_line(rule):
    if not isinstance(rule, dict):
        return str(rule)
    key = rule.get('key', rule.get('rule', 'Policy rule'))
    params = rule.get('params')
    if isinstance(params, dict):
        details = dict(params)
    else:
        details = {
            name: value for name, value in rule.items()
            if name not in {'key', 'rule', 'hard', 'priority'}
        }
    description = f'{_humanize(key)}'
    if details:
        description += ': ' + ', '.join(
            f'{_humanize(name)} {_policy_value(value)}'
            for name, value in details.items()
        )
    qualifiers = []
    if 'hard' in rule:
        qualifiers.append('hard' if rule['hard'] else 'soft')
    if rule.get('priority') in (1, 2, 3):
        qualifiers.append({1: 'high', 2: 'medium', 3: 'low'}[rule['priority']] + ' priority')
    if qualifiers:
        description += ' (' + ', '.join(qualifiers) + ')'
    return description


def _humanize(value):
    return str(value).replace('_', ' ').replace('-', ' ').capitalize()


def _policy_value(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _violation_groups(violations):
    normalized = [item for item in violations if isinstance(item, dict)]
    normalized.sort(key=lambda item: (
        not item.get('hard', False),
        item.get('priority', 4) if isinstance(item.get('priority'), int) else 4,
        _natural_sort_key(item.get('rule', '')),
        _natural_sort_key(item.get('team') or ''),
    ))
    groups = []
    for violation in normalized:
        key = (violation.get('hard', False), violation.get('priority'), violation.get('rule'))
        if not groups or groups[-1]['key'] != key:
            priority = violation.get('priority')
            priority_label = {1: 'High', 2: 'Medium', 3: 'Low'}.get(priority)
            label = _humanize(violation.get('rule', 'Rule'))
            label += ' (hard)' if violation.get('hard') else ' (soft)'
            if priority_label:
                label += f' - {priority_label} priority'
            groups.append({'key': key, 'label': label, 'violations': []})
        groups[-1]['violations'].append(violation)
    return [{'label': group['label'], 'violations': group['violations']} for group in groups]


@login_required
def project_detail(request, project_id):
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    runs = project.runs.select_related('cohort').annotate(
        team_count=Count('teams', distinct=True),
        student_count=Count('cohort__students', distinct=True),
    ).order_by('-created_at')
    for run in runs:
        run.policy_lines = _policy_lines(run.policy_snapshot)
    return render(request, 'project_detail.html', {
        'project': project,
        'runs': runs,
        'has_cohorts': project.cohorts.exists(),
    })


@login_required
def run_detail(request, run_id):
    run = _owned_run(request.user, run_id)
    if run.status != AllocationRun.Status.OK:
        return render(request, 'run_failed.html', {
            'run': run,
            'policy_lines': _policy_lines(run.policy_snapshot),
        })
    ordered_team_rows = list(run.teams.values_list('pk', 'name'))
    ordered_team_rows.sort(key=lambda row: _natural_sort_key(row[1]))
    team_page = Paginator(ordered_team_rows, 50).get_page(request.GET.get('page'))
    page_team_ids = [team_id for team_id, _ in team_page.object_list]
    teams_by_id = {
        team.pk: team
        for team in run.teams.filter(pk__in=page_team_ids)
        .annotate(member_count=Count('members'))
        .prefetch_related('members__student')
    }
    teams = [teams_by_id[team_id] for team_id in page_team_ids]
    violation_teams = {item.get('team') for item in run.violations if isinstance(item, dict)}
    for team in teams:
        team.has_violation = team.name in violation_teams
    student_count = run.cohort.students.count()
    allocated_count = TeamMembership.objects.filter(team__run=run).count()
    team_page.object_list = teams
    return render(request, 'run_detail.html', {
        'run': run, 'teams': team_page.object_list, 'team_page': team_page,
        'team_count': len(ordered_team_rows),
        'student_count': student_count, 'allocated_count': allocated_count,
        'unmet_rules': run.violations,
        'unmet_rule_groups': _violation_groups(run.violations),
        'unmet_rule_count': len(run.violations),
        'policy_lines': _policy_lines(run.policy_snapshot),
    })


@login_required
def export_run_csv(request, run_id):
    run = _owned_run(request.user, run_id, status=AllocationRun.Status.OK)
    filename = re.sub(r'[^A-Za-z0-9_-]+', '-', run.project.name).strip('-').lower() or 'project'
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}-run-{run.pk}.csv"'
    writer = csv.writer(response)
    writer.writerow(['first_name', 'last_name', 'email', 'team'])
    memberships = TeamMembership.objects.filter(team__run=run).select_related('student', 'team')
    rows = sorted(
        ((membership.team.name, membership.student.first_name, membership.student.last_name, membership.student.email)
         for membership in memberships),
        key=lambda row: (_natural_sort_key(row[0]), (row[2] or '').casefold(), (row[1] or '').casefold(), row[3] or ''),
    )
    for team_name, first_name, last_name, email in rows:
        writer.writerow([first_name, last_name, email, team_name])
    return response
