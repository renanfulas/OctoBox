import os
import sys
import unittest
from datetime import datetime


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from onboarding.attribution import (
    build_intake_attribution_payload,
    extract_acquisition_channel,
    merge_qualification_response,
    summarize_acquisition_channels,
)


class OnboardingAttributionTest(unittest.TestCase):
    def test_build_payload_separates_operational_source_from_acquisition_channel(self):
        payload = build_intake_attribution_payload(
            source='manual',
            acquisition_channel='instagram',
            acquisition_detail='story da unidade',
            entry_kind='lead',
            actor_id=9,
            captured_at=datetime(2026, 4, 9, 10, 30, 0),
        )

        self.assertEqual(payload['entry_kind'], 'lead')
        self.assertEqual(payload['attribution']['operational_source'], 'manual')
        self.assertEqual(payload['attribution']['acquisition']['declared_channel'], 'instagram')
        self.assertEqual(payload['attribution']['acquisition']['declared_detail'], 'story da unidade')
        self.assertEqual(payload['attribution']['captured_by_actor_id'], 9)

    def test_confirmed_channel_wins_over_declared_channel(self):
        payload = build_intake_attribution_payload(
            source='manual',
            acquisition_channel='instagram',
        )
        qualified_payload = merge_qualification_response(
            raw_payload=payload,
            confirmed_channel='referral',
            confirmed_detail='amiga da aluna',
            response_channel='google_forms',
        )

        self.assertEqual(
            extract_acquisition_channel(raw_payload=qualified_payload, fallback_source='manual'),
            'referral',
        )

    def test_legacy_source_fallback_keeps_old_records_usable(self):
        self.assertEqual(
            extract_acquisition_channel(raw_payload={}, fallback_source='csv'),
            'referral',
        )
        self.assertEqual(
            extract_acquisition_channel(raw_payload=None, fallback_source='whatsapp'),
            'whatsapp',
        )

    def test_summarize_channels_counts_missing_rows(self):
        rows = [
            ('manual', build_intake_attribution_payload(source='manual', acquisition_channel='instagram')),
            ('csv', {}),
            ('manual', {}),
        ]

        summary = summarize_acquisition_channels(rows)

        self.assertEqual(summary['instagram'], 1)
        self.assertEqual(summary['referral'], 1)
        self.assertEqual(summary['missing'], 1)


if __name__ == '__main__':
    unittest.main()
