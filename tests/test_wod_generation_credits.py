from datetime import date

from django.test import TestCase

from operations.services.wod_generation_credits import (
    FREE_CREDITS_PER_MONTH,
    add_purchased_credits,
    consume_wod_generation_credit,
    get_or_create_current_ledger,
)
from student_app.models import WodGenerationCreditLedger


class WodGenerationCreditsTests(TestCase):
    def test_get_or_create_current_ledger_starts_at_period_first_day(self):
        ledger = get_or_create_current_ledger(today=date(2026, 8, 15))
        self.assertEqual(ledger.period_start, date(2026, 8, 1))
        self.assertEqual(ledger.free_credits_total, FREE_CREDITS_PER_MONTH)
        self.assertEqual(ledger.free_credits_used, 0)
        self.assertEqual(ledger.credits_remaining, FREE_CREDITS_PER_MONTH)

    def test_get_or_create_current_ledger_is_idempotent_within_same_month(self):
        first = get_or_create_current_ledger(today=date(2026, 8, 1))
        first.free_credits_used = 1
        first.save(update_fields=['free_credits_used'])

        second = get_or_create_current_ledger(today=date(2026, 8, 31))

        self.assertEqual(first.id, second.id)
        self.assertEqual(second.free_credits_used, 1)
        self.assertEqual(WodGenerationCreditLedger.objects.count(), 1)

    def test_new_month_resets_credits_via_new_ledger_row(self):
        get_or_create_current_ledger(today=date(2026, 8, 15)).free_credits_used = FREE_CREDITS_PER_MONTH
        WodGenerationCreditLedger.objects.filter(period_start=date(2026, 8, 1)).update(
            free_credits_used=FREE_CREDITS_PER_MONTH,
        )

        september_ledger = get_or_create_current_ledger(today=date(2026, 9, 1))

        self.assertEqual(september_ledger.period_start, date(2026, 9, 1))
        self.assertEqual(september_ledger.free_credits_used, 0)
        self.assertEqual(september_ledger.credits_remaining, FREE_CREDITS_PER_MONTH)
        self.assertEqual(WodGenerationCreditLedger.objects.count(), 2)

    def test_consume_spends_free_credits_first(self):
        today = date(2026, 8, 15)
        self.assertTrue(consume_wod_generation_credit(today=today))
        self.assertTrue(consume_wod_generation_credit(today=today))

        ledger = WodGenerationCreditLedger.objects.get(period_start=date(2026, 8, 1))
        self.assertEqual(ledger.free_credits_used, FREE_CREDITS_PER_MONTH)
        self.assertEqual(ledger.purchased_credits_available, 0)

    def test_consume_blocks_when_quota_exhausted(self):
        today = date(2026, 8, 15)
        for _ in range(FREE_CREDITS_PER_MONTH):
            self.assertTrue(consume_wod_generation_credit(today=today))

        self.assertFalse(consume_wod_generation_credit(today=today))

        ledger = WodGenerationCreditLedger.objects.get(period_start=date(2026, 8, 1))
        self.assertEqual(ledger.free_credits_used, FREE_CREDITS_PER_MONTH)

    def test_consume_falls_back_to_purchased_credits_after_free_exhausted(self):
        today = date(2026, 8, 15)
        add_purchased_credits(3, today=today)
        for _ in range(FREE_CREDITS_PER_MONTH):
            consume_wod_generation_credit(today=today)

        self.assertTrue(consume_wod_generation_credit(today=today))

        ledger = WodGenerationCreditLedger.objects.get(period_start=date(2026, 8, 1))
        self.assertEqual(ledger.purchased_credits_available, 2)
        self.assertEqual(ledger.credits_remaining, 2)

    def test_add_purchased_credits_rejects_non_positive_amount(self):
        with self.assertRaises(ValueError):
            add_purchased_credits(0)
