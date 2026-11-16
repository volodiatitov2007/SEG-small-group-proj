"""Views for managing projects."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from allocations.models import Project


@login_required
def project_list(request):
    """Show the logged-in user's projects, newest first."""
    projects = Project.objects.filter(owner=request.user).order_by('-created_at')
    return render(request, 'project_list.html', {'projects': projects})
