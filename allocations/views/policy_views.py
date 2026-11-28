"""Views for the allocation policies of a project."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from allocations.forms import PolicyForm
from allocations.models import Policy, Project
from allocations.policies import describe_rules


@login_required
def policy_list(request, project_id):
    """Show the policies of a project the user owns, with their rules."""
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    policies = list(project.policies.all())
    for policy in policies:
        policy.rule_lines = describe_rules(policy.rules)
    return render(request, 'policy_list.html', {'project': project, 'policies': policies})


@login_required
def policy_create(request, project_id):
    """Let the owner of a project create a policy for it."""
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    if request.method == 'POST':
        form = PolicyForm(request.POST, project=project)
        if form.is_valid():
            policy = form.save()
            messages.success(request, f'Policy {policy.name} has been saved.')
            return redirect('policy_list', project_id=project.id)
    else:
        form = PolicyForm(project=project)
    return render(request, 'policy_form.html', {'form': form, 'project': project, 'title': 'New policy'})


@login_required
def policy_update(request, policy_id):
    """Let the owner of a policy's project change its rules."""
    policy = get_object_or_404(Policy.objects.select_related('project'), pk=policy_id, project__owner=request.user)
    if request.method == 'POST':
        form = PolicyForm(request.POST, project=policy.project, policy=policy)
        if form.is_valid():
            form.save()
            messages.success(request, f'Policy {policy.name} has been updated.')
            return redirect('policy_list', project_id=policy.project.id)
    else:
        form = PolicyForm(project=policy.project, policy=policy)
        if form.unreadable_rules:
            unknown = ', '.join(f"'{key}'" for key in form.unreadable_rules)
            messages.warning(request, f'This policy has rules the app no longer knows ({unknown}). '
                                      'Saving the form replaces them with the rules chosen below.')
    return render(request, 'policy_form.html', {
        'form': form, 'project': policy.project, 'title': f'Edit policy {policy.name}',
    })
