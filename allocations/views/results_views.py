import csv
import re

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render

from allocations.models import AllocationRun, Project, TeamMembership


def _owned_run(user, run_id, **filters):
    return get_object_or_404(AllocationRun.objects.select_related('project', 'cohort'),
                             pk=run_id, project__owner=user, **filters)


@login_required
def project_detail(request, project_id):
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    runs = project.runs.select_related('cohort').prefetch_related('teams__members').order_by('-created_at')
    return render(request, 'project_detail.html', {'project': project, 'runs': runs})


@login_required
def run_detail(request, run_id):
    run = _owned_run(request.user, run_id)
    if run.status != AllocationRun.Status.OK:
        return render(request, 'run_failed.html', {'run': run})
    teams = run.teams.prefetch_related('members__student').all()
    violation_teams = {item.get('team') for item in run.violations if isinstance(item, dict)}
    for team in teams:
        team.has_violation = team.name in violation_teams
    student_count = run.cohort.students.count()
    allocated_count = sum(team.members.count() for team in teams)
    return render(request, 'run_detail.html', {
        'run': run, 'teams': teams, 'team_count': len(teams),
        'student_count': student_count, 'allocated_count': allocated_count,
        'unmet_rules': run.violations,
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
        key=lambda row: (row[0], (row[2] or '').casefold(), (row[1] or '').casefold(), row[3] or ''),
    )
    for team_name, first_name, last_name, email in rows:
        writer.writerow([first_name, last_name, email, team_name])
    return response
