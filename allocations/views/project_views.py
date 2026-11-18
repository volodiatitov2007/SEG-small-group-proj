"""Views for managing projects."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from allocations.forms import ProjectForm
from allocations.models import Project


@login_required
def project_list(request):
    """Show the logged-in user's projects, newest first."""
    projects = Project.objects.filter(owner=request.user).order_by('-created_at')
    return render(request, 'project_list.html', {'projects': projects})


@login_required
def project_create(request):
    """Let the logged-in user create a project, which they then own."""
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.owner = request.user
            project.save()
            messages.success(request, f'Project {project.name} has been created.')
            return redirect('project_detail', project_id=project.id)
    else:
        form = ProjectForm()
    return render(request, 'project_form.html', {'form': form, 'title': 'Create project'})


@login_required
def project_update(request, project_id):
    """Let the owner change a project's name and description."""
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, f'Project {project.name} has been updated.')
            return redirect('project_detail', project_id=project.id)
    else:
        form = ProjectForm(instance=project)
    return render(request, 'project_form.html', {'form': form, 'title': 'Edit project'})


@login_required
def project_delete(request, project_id):
    """Ask the owner for confirmation, then delete the project."""
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    if request.method == 'POST':
        project.delete()
        messages.success(request, f'Project {project.name} has been deleted.')
        return redirect('project_list')
    return render(request, 'project_confirm_delete.html', {'project': project})
