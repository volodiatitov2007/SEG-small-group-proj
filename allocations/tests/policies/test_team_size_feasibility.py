from django.test import SimpleTestCase

from allocations.policies.evaluator import team_size_feasible, team_size_problem


class TeamSizeFeasibilityTestCase(SimpleTestCase):
    """Tests of the team-size pre-check that detects known-impossible cases."""

    def test_feasible_cohort_sizes_for_4_to_5(self):
        for count in (4, 5, 8, 9, 10, 12, 300):
            with self.subTest(count=count):
                self.assertTrue(team_size_feasible(count, 4, 5))

    def test_infeasible_cohort_sizes_for_4_to_5(self):
        for count in (1, 2, 3, 6, 7, 11):
            with self.subTest(count=count):
                self.assertFalse(team_size_feasible(count, 4, 5))

    def test_every_size_from_12_up_is_feasible_for_4_to_5(self):
        for count in range(12, 400):
            with self.subTest(count=count):
                self.assertTrue(team_size_feasible(count, 4, 5))

    def test_agrees_with_brute_force(self):
        for min_size in range(1, 6):
            for max_size in range(min_size, 8):
                for count in range(1, 40):
                    expected = any(
                        k * min_size <= count <= k * max_size for k in range(1, count + 1)
                    )
                    with self.subTest(count=count, min=min_size, max=max_size):
                        self.assertEqual(team_size_feasible(count, min_size, max_size), expected)

    def test_reason_explains_impossible_split(self):
        self.assertEqual(
            team_size_problem(7, 4, 5),
            "7 students cannot be split into teams of 4-5.",
        )

    def test_no_reason_when_feasible(self):
        self.assertIsNone(team_size_problem(300, 4, 5))

    def test_zero_students_is_reported(self):
        self.assertEqual(team_size_problem(0, 4, 5), "There are no students to allocate.")

    def test_minimum_above_maximum_is_reported(self):
        self.assertEqual(team_size_problem(10, 6, 5), "Team sizes 6-5 are not a valid range.")

    def test_minimum_below_one_is_reported(self):
        self.assertIsNotNone(team_size_problem(10, 0, 5))

    def test_returns_a_plain_boolean(self):
        self.assertIs(team_size_feasible(300, 4, 5), True)
        self.assertIs(team_size_feasible(7, 4, 5), False)
        self.assertIs(team_size_feasible(0, 4, 5), False)
        self.assertIs(team_size_feasible(10, 6, 5), False)
