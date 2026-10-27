from django.test import SimpleTestCase
from django.core import signing
from django_tenants.utils import schema_context
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from operations.services.wod_input_contracts import duplicate_weekday_errors
from operations.services.wod_preview_contracts import issue_projection_token, read_projection_token


class WodInputContractTests(SimpleTestCase):
    def test_duplicate_weekday_reports_both_source_lines(self):
        source = 'SEGUNDA-FEIRA\nForça\nTERÇA\nMetcon\nSEGUNDA:\nOutro bloco'
        errors = duplicate_weekday_errors(source)
        self.assertEqual(len(errors), 1)
        self.assertIn('Linha 5', errors[0])
        self.assertIn('linha 1', errors[0])

    def test_one_section_per_weekday_is_allowed(self):
        self.assertEqual(duplicate_weekday_errors('SEGUNDA-FEIRA\nForça\nTERÇA\nMetcon'), [])

    def test_weekly_preview_token_cannot_cross_tenants_even_on_replay(self):
        with schema_context('box_preview_a'), patch(
            'operations.services.wod_preview_contracts.projection_contract_fingerprint', return_value='a' * 64,
        ):
            token = issue_projection_token(
                weekly_plan=SimpleNamespace(pk=1), target_week_start=date(2026, 10, 19),
                class_types=['CROSS'], actor=SimpleNamespace(pk=1), preview={}, intent_id=uuid4(),
            )
            self.assertEqual(read_projection_token(token)['actor_id'], 1)
        with schema_context('box_preview_b'):
            for allow_expired in (False, True):
                with self.subTest(allow_expired=allow_expired), self.assertRaises(signing.BadSignature):
                    read_projection_token(token, allow_expired=allow_expired)
