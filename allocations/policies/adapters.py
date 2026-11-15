"""Turn stored students into the read-only StudentView that rules and the allocator use."""
from .base import StudentView


def student_view(student) -> StudentView:
    """Build a StudentView from a Student row.

    Any object with id, first_name, last_name, gender, ethnicity, c_score and extra works,
    so this module needs no Django import.
    """
    return StudentView(
        id=student.id,
        name=f'{student.first_name} {student.last_name}'.strip(),
        gender=student.gender,
        ethnicity=student.ethnicity,
        c_score=student.c_score,
        extra=dict(student.extra or {}),
    )
