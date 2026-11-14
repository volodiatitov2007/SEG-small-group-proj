"""Read and check an uploaded cohort CSV file.

There are no Django views or models in here, so it can be tested on its own.
"""

import csv
import io
from dataclasses import dataclass, field

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

REQUIRED_COLUMNS = ['first_name', 'last_name', 'email']


@dataclass
class Problem:
    """Something wrong with the uploaded file."""

    row_number: int | None
    column: str
    value: str
    message: str


@dataclass
class ImportResult:
    """What came out of reading a cohort file."""

    rows: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


def parse_cohort_csv(uploaded_file):
    """Read a cohort CSV file and return its rows, errors, and warnings."""
    result = ImportResult()
    text = uploaded_file.read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text))
    columns = reader.fieldnames or []

    for column in REQUIRED_COLUMNS:
        if column not in columns:
            result.errors.append(Problem(
                row_number=None,
                column=column,
                value='',
                message=f"Required column '{column}' is missing. Columns found: {', '.join(columns)}.",
            ))

    if result.errors:
        return result

    seen_emails = {}
    for row_number, row in enumerate(reader, start=2):
        _check_required_values(row, row_number, result)
        _check_email(row, row_number, seen_emails, result)

    return result


def _check_required_values(row, row_number, result):
    """Report any required column that is empty in this row."""
    for column in REQUIRED_COLUMNS:
        value = (row[column] or '').strip()
        if not value:
            result.errors.append(Problem(
                row_number=row_number,
                column=column,
                value='',
                message=f'Row {row_number}: {column} is empty. Every student needs a first name, last name, and email.',
            ))


def _check_email(row, row_number, seen_emails, result):
    """Report an email that is invalid, or already used on an earlier row."""
    email = (row['email'] or '').strip()
    if not email:
        return

    try:
        validate_email(email)
    except ValidationError:
        result.errors.append(Problem(
            row_number=row_number,
            column='email',
            value=email,
            message=f"Row {row_number}: '{email}' is not a valid email address.",
        ))
        return

    key = email.lower()
    if key in seen_emails:
        result.errors.append(Problem(
            row_number=row_number,
            column='email',
            value=email,
            message=f'Row {row_number}: {email} is already used on row {seen_emails[key]}.',
        ))
    else:
        seen_emails[key] = row_number
