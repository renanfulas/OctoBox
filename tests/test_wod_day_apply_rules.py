"""
Testes das regras puras de aplicação de template por dia.

Cobre evaluate_session_eligibility e filter_eligible_sessions sem
tocar em banco, request ou cache.
"""

import unittest

from operations.domain.wod_day_apply_rules import (
    evaluate_session_eligibility,
    filter_eligible_sessions,
)


class EvaluateSessionEligibilityTests(unittest.TestCase):
    def test_replace_empty_skips_session_with_existing_workout(self):
        result = evaluate_session_eligibility(
            session_id=1,
            has_existing_workout=True,
            mode='replace_empty',
        )
        self.assertFalse(result.eligible)
        self.assertIn('já possui WOD', result.skip_reason)

    def test_replace_empty_allows_session_without_workout(self):
        result = evaluate_session_eligibility(
            session_id=2,
            has_existing_workout=False,
            mode='replace_empty',
        )
        self.assertTrue(result.eligible)
        self.assertEqual(result.skip_reason, '')

    def test_overwrite_allows_session_with_existing_workout(self):
        result = evaluate_session_eligibility(
            session_id=3,
            has_existing_workout=True,
            mode='overwrite',
        )
        self.assertTrue(result.eligible)

    def test_overwrite_allows_session_without_workout(self):
        result = evaluate_session_eligibility(
            session_id=4,
            has_existing_workout=False,
            mode='overwrite',
        )
        self.assertTrue(result.eligible)

    def test_result_carries_session_id(self):
        result = evaluate_session_eligibility(
            session_id=99,
            has_existing_workout=False,
            mode='replace_empty',
        )
        self.assertEqual(result.session_id, 99)


class FilterEligibleSessionsTests(unittest.TestCase):
    def _make_session(self, session_id, has_existing_workout):
        return {'session_id': session_id, 'has_existing_workout': has_existing_workout}

    def test_separates_eligible_and_skipped_in_replace_empty_mode(self):
        sessions = [
            self._make_session(1, has_existing_workout=False),
            self._make_session(2, has_existing_workout=True),
            self._make_session(3, has_existing_workout=False),
        ]
        eligible, skipped = filter_eligible_sessions(sessions=sessions, mode='replace_empty')

        self.assertEqual(len(eligible), 2)
        self.assertEqual(len(skipped), 1)
        self.assertEqual(skipped[0].session_id, 2)

    def test_all_sessions_eligible_in_overwrite_mode(self):
        sessions = [
            self._make_session(1, has_existing_workout=True),
            self._make_session(2, has_existing_workout=True),
        ]
        eligible, skipped = filter_eligible_sessions(sessions=sessions, mode='overwrite')

        self.assertEqual(len(eligible), 2)
        self.assertEqual(len(skipped), 0)

    def test_empty_list_returns_empty_results(self):
        eligible, skipped = filter_eligible_sessions(sessions=[], mode='replace_empty')
        self.assertEqual(eligible, [])
        self.assertEqual(skipped, [])


if __name__ == '__main__':
    unittest.main()
