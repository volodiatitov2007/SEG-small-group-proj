"""Views for uploading and viewing cohorts."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from allocations.models import Cohort


@login_required
def cohort_detail(request, cohort_id):
    """Show the students in one of the logged-in user's cohorts."""
    cohort = get_object_or_404(Cohort, pk=cohort_id, project__owner=request.user)
    return render(request, 'cohort_detail.html', {'cohort': cohort, 'students': cohort.students.all()})
