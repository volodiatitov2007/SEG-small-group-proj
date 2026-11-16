"""Views for managing projects."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

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
