from allocations.policies import StudentView


def make_students(count, start=1, **attributes):
    """Make `count` students with consecutive ids and the given attributes."""
    return [
        StudentView(id=i, name=f"Student {i}", **attributes)
        for i in range(start, start + count)
    ]


def make_teams(*sizes):
    """Make teams named "Team 1", "Team 2"... with the given sizes and unique students."""
    teams, next_id = {}, 1
    for number, size in enumerate(sizes, start=1):
        teams[f"Team {number}"] = make_students(size, start=next_id)
        next_id += size
    return teams
