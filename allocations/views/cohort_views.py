"""Views for uploading and viewing cohorts."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from allocations.cohort_import import save_cohort
from allocations.csv_import import parse_cohort_csv
from allocations.forms import CohortUploadForm
from allocations.models import Cohort, Project

STUDENTS_PER_PAGE = 50


@login_required
def cohort_upload(request, project_id):
    """Let the owner upload a cohort CSV file, saving the good rows and listing the problems."""
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    result = None
    if request.method == 'POST':
        form = CohortUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data['file']
            result = parse_cohort_csv(uploaded_file)
            if not result.file_errors:
                cohort = save_cohort(project, uploaded_file.name, result)
                request.session[f'cohort_upload_{cohort.id}'] = {
                    'bad_rows': [problem.message for problem in result.bad_rows],
                    'warnings': [problem.message for problem in result.warnings],
                }
                skipped = len({problem.row_number for problem in result.bad_rows})
                messages.success(request, f'Uploaded {uploaded_file.name}: imported {len(result.rows)}, skipped {skipped}.')
                return redirect('cohort_detail', cohort_id=cohort.id)
    else:
        form = CohortUploadForm()
    return render(request, 'cohort_upload.html', {'project': project, 'form': form, 'result': result})


@login_required
def cohort_detail(request, cohort_id):
    """Show the students in one of the logged-in user's cohorts, and any problems from its upload."""
    cohort = get_object_or_404(Cohort, pk=cohort_id, project__owner=request.user)
    upload = request.session.pop(f'cohort_upload_{cohort.id}', None)
    page = Paginator(cohort.students.all(), STUDENTS_PER_PAGE).get_page(request.GET.get('page'))
    return render(request, 'cohort_detail.html', {'cohort': cohort, 'page': page, 'upload': upload})
