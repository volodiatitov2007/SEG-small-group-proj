from django.test import SimpleTestCase

from allocations.allocator import OK, allocate
from allocations.policies import GenderRule, StudentView, TeamSizeRule, rule_from_dict
from allocations.policies.evaluator import is_valid

WOMAN, MAN, OTHER, NOT_GIVEN = 1, 2, 3, 0


def student(number, gender, name=None):
    return StudentView(id=number, name=name or f'Student {number}', gender=gender)


def cohort(*genders):
    """Make one student per gender code, with ids 1, 2, 3..."""
    return [student(number, gender) for number, gender in enumerate(genders, start=1)]


class GenderRuleTestCase(SimpleTestCase):
    """Tests of GenderRule on single teams, in a cohort with several women and men."""

    def setUp(self):
        self.rule = GenderRule()
        self.rule.prepare(cohort(WOMAN, WOMAN, WOMAN, MAN, MAN, MAN, OTHER, NOT_GIVEN, None))

    def check(self, *genders):
        return self.rule.check_team('Team 1', cohort(*genders))

    def test_two_women_and_two_men_pass(self):
        self.assertEqual(self.check(WOMAN, WOMAN, MAN, MAN), [])

    def test_team_of_one_gender_passes(self):
        self.assertEqual(self.check(MAN, MAN, MAN, MAN), [])

    def test_only_woman_in_team_is_flagged(self):
        team = [student(1, WOMAN, 'Priya Shah'), student(2, MAN), student(3, MAN), student(4, MAN)]
        [violation] = self.rule.check_team('Team 3', team)
        self.assertEqual(violation.message, 'Team 3 has only one woman (Priya Shah).')
        self.assertEqual(violation.team, 'Team 3')
        self.assertEqual(violation.amount, 1)

    def test_only_man_in_team_is_flagged(self):
        [violation] = self.check(MAN, WOMAN, WOMAN, WOMAN)
        self.assertEqual(violation.message, 'Team 1 has only one man (Student 1).')

    def test_two_lone_students_give_one_violation_with_amount_two(self):
        [violation] = self.check(WOMAN, MAN, NOT_GIVEN, NOT_GIVEN)
        self.assertEqual(
            violation.message, 'Team 1 has only one woman (Student 1) and only one man (Student 2).',
        )
        self.assertEqual(violation.amount, 2)

    def test_not_given_gender_is_never_flagged(self):
        self.assertEqual(self.check(NOT_GIVEN, MAN, MAN, MAN), [])

    def test_missing_gender_column_is_never_flagged(self):
        self.assertEqual(self.check(None, MAN, MAN, MAN), [])

    def test_team_of_only_unknown_genders_passes(self):
        self.assertEqual(self.check(NOT_GIVEN, NOT_GIVEN, None, None), [])

    def test_unknown_gender_does_not_count_as_company(self):
        [violation] = self.check(WOMAN, NOT_GIVEN, None, NOT_GIVEN)
        self.assertEqual(violation.message, 'Team 1 has only one woman (Student 1).')

    def test_other_gender_student_in_gender_diverse_team_passes(self):
        self.assertEqual(self.check(OTHER, MAN, MAN, MAN), [])

    def test_other_gender_student_with_no_other_disclosed_gender_is_flagged(self):
        [violation] = self.check(OTHER, NOT_GIVEN, NOT_GIVEN, None)
        self.assertEqual(
            violation.message,
            'Team 1 has only one other/non-binary student (Student 1) and no other disclosed gender.',
        )

    def test_two_other_gender_students_together_pass(self):
        self.assertEqual(self.check(OTHER, OTHER, NOT_GIVEN, NOT_GIVEN), [])

    def test_check_team_gives_the_same_result_as_check_allocation(self):
        teams = {'Team 1': cohort(WOMAN, MAN, MAN), 'Team 2': cohort(WOMAN, WOMAN, MAN, MAN)}
        one_by_one = [v for name, members in teams.items() for v in self.rule.check_team(name, members)]
        self.assertEqual(one_by_one, self.rule.check_allocation(teams))


class GenderRuleCohortTestCase(SimpleTestCase):
    """Tests of how the whole cohort, counted by prepare(), changes what is flagged."""

    def test_only_woman_in_the_cohort_passes_in_a_gender_diverse_team(self):
        rule = GenderRule()
        rule.prepare(cohort(WOMAN, MAN, MAN, MAN, MAN))
        self.assertEqual(rule.check_team('Team 1', cohort(WOMAN, MAN, MAN, MAN)), [])

    def test_only_woman_in_the_cohort_is_flagged_without_another_disclosed_gender(self):
        rule = GenderRule()
        rule.prepare(cohort(WOMAN, NOT_GIVEN, NOT_GIVEN, MAN))
        [violation] = rule.check_team('Team 1', cohort(WOMAN, NOT_GIVEN, NOT_GIVEN))
        self.assertIn('no other disclosed gender', violation.message)

    def test_prepare_ignores_unknown_genders(self):
        rule = GenderRule()
        rule.prepare(cohort(WOMAN, NOT_GIVEN, None, NOT_GIVEN))
        self.assertEqual(rule.check_team('Team 1', cohort(WOMAN, MAN, MAN)), [])

    def test_without_prepare_a_lone_woman_is_flagged(self):
        [violation] = GenderRule().check_team('Team 1', cohort(WOMAN, MAN, MAN, MAN))
        self.assertEqual(violation.message, 'Team 1 has only one woman (Student 1).')

    def test_prepare_again_replaces_the_old_counts(self):
        rule = GenderRule()
        rule.prepare(cohort(WOMAN, WOMAN, MAN))
        rule.prepare(cohort(WOMAN, MAN, MAN))
        self.assertEqual(rule.check_team('Team 1', cohort(WOMAN, MAN, MAN)), [])


class GenderRuleSettingsTestCase(SimpleTestCase):
    """Tests of the gender rule's settings and saved form."""

    def test_is_soft_with_high_priority_by_default(self):
        rule = GenderRule()
        self.assertFalse(rule.hard)
        self.assertEqual(rule.priority, 1)

    def test_violation_carries_rule_settings(self):
        rule = GenderRule(hard=True, priority=2)
        [violation] = rule.check_team('Team 4', cohort(WOMAN, MAN, MAN))
        self.assertEqual(violation.rule, 'gender')
        self.assertTrue(violation.hard)
        self.assertEqual(violation.priority, 2)

    def test_to_dict(self):
        self.assertEqual(GenderRule(priority=2).to_dict(), {'key': 'gender', 'hard': False, 'priority': 2})

    def test_round_trip_through_rule_from_dict_gives_equal_rule(self):
        rule = GenderRule(hard=True, priority=3)
        restored = rule_from_dict(rule.to_dict())
        self.assertIsInstance(restored, GenderRule)
        self.assertEqual(restored, rule)

    def test_describe(self):
        self.assertEqual(GenderRule(priority=2).describe(), 'Gender representation (soft, priority 2)')


class GenderRuleWithAllocatorTestCase(SimpleTestCase):
    """A hard gender rule must never make an ordinary cohort impossible."""

    def allocate(self, students):
        rules = [TeamSizeRule(4, 5), GenderRule(hard=True)]
        result = allocate(students, rules, time_limit=5.0, seed=0)
        self.assertEqual(result.status, OK, result.message)
        self.assertTrue(is_valid(rules, result.teams))

    def test_one_woman_in_the_cohort_can_still_be_allocated(self):
        self.allocate(cohort(WOMAN, MAN, MAN, MAN, MAN, MAN, MAN, MAN, MAN))

    def test_two_women_are_placed_together(self):
        self.allocate(cohort(WOMAN, WOMAN, MAN, MAN, MAN, MAN, MAN, MAN, MAN))

    def test_one_other_gender_student_can_still_be_allocated(self):
        self.allocate(cohort(OTHER, MAN, MAN, MAN, WOMAN, WOMAN, MAN, MAN, NOT_GIVEN))
