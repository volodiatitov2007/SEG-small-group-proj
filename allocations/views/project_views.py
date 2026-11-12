"""Views for managing projects."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from allocations.models import Project


@login_required
def project_list(request):
    """Show a list of all projects."""
    projects = Project.objects.all()
    return render(request, 'project_list.html', {'projects': projects})
