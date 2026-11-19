from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from allocations import services
from allocations.models import Project
from allocations.policies import TeamSizeRule

# shortcut: no Policy model on main yet, swap in the project's policy when Wasif's Policy lands
DEFAULT_RULES = [TeamSizeRule(4, 5).to_dict()]


@login_required
@require_POST
def start_run(request, project_id):
    """Run an allocation on the project's latest cohort, then show the run."""
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    cohort = project.cohorts.order_by('-uploaded_at', '-pk').first()
    if cohort is None:
        messages.error(request, 'Upload a cohort CSV before running an allocation.')
        return redirect('project_detail', project_id=project.id)
    run = services.run_allocation(cohort, DEFAULT_RULES)
    return redirect('run_detail', run_id=run.id)
