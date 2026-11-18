"""Save a checked cohort CSV file to the database."""

from django.db import transaction

from allocations.models import Cohort, Student


@transaction.atomic
def save_cohort(project, filename, result):
    """Save the good rows of a checked cohort file as a new cohort of the project."""
    cohort = Cohort.objects.create(project=project, original_filename=filename, columns=result.columns)
    Student.objects.bulk_create([Student(cohort=cohort, **row) for row in result.rows])
    return cohort
