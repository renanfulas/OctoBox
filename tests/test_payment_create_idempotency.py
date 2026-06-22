"""
ARQUIVO: testes do guard de duplo-submit do create-payment (F8).

POR QUE EXISTE:
- O create-payment avulso nao tinha protecao contra duplo-clique / re-POST: cada
  submit criava uma cobranca. O decorator @idempotent_action so age quando o
  cliente manda X-Idempotency-Key (opt-in) — este guard cobre o caso real (sem
  header), derivando a chave do conteudo do submit, com janela curta via cache.
"""

from __future__ import annotations

from types import SimpleNamespace

from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.management import call_command
from django.test import RequestFactory, TestCase
from django.urls import reverse

from access.roles import ROLE_OWNER
from shared_support.security.fintech_throttles import (
    claim_create_payment_idempotency,
    release_create_payment_idempotency,
)
from tests.factories import StudentFactory, UserFactory


class CreatePaymentIdempotencyHelperTests(TestCase):
    def setUp(self):
        cache.clear()

    def _request(self, user_id=7):
        request = RequestFactory().post('/')
        request.user = SimpleNamespace(id=user_id)
        return request

    def _data(self, amount='100.00', due='2026-07-01'):
        return {'amount': amount, 'due_date': due}

    def test_first_claim_succeeds_and_duplicate_is_blocked(self):
        request = self._request()
        student = SimpleNamespace(id=1)
        data = self._data()

        key = claim_create_payment_idempotency(request, student, data)
        self.assertIsNotNone(key)
        self.assertIsNone(claim_create_payment_idempotency(request, student, data))

    def test_release_allows_immediate_reclaim(self):
        request = self._request()
        student = SimpleNamespace(id=1)
        data = self._data()

        key = claim_create_payment_idempotency(request, student, data)
        release_create_payment_idempotency(key)
        self.assertIsNotNone(claim_create_payment_idempotency(request, student, data))

    def test_different_amount_or_student_not_blocked(self):
        request = self._request()
        self.assertIsNotNone(
            claim_create_payment_idempotency(request, SimpleNamespace(id=1), self._data(amount='100.00'))
        )
        self.assertIsNotNone(
            claim_create_payment_idempotency(request, SimpleNamespace(id=1), self._data(amount='200.00'))
        )
        self.assertIsNotNone(
            claim_create_payment_idempotency(request, SimpleNamespace(id=2), self._data(amount='100.00'))
        )


class CreatePaymentDoubleSubmitTests(TestCase):
    """Integração: dois POSTs identicos de create-payment criam UMA cobranca."""

    def setUp(self):
        cache.clear()
        call_command('bootstrap_roles')
        self.owner = UserFactory(username='f8-owner')
        self.owner.groups.add(Group.objects.get(name=ROLE_OWNER))
        self.student = StudentFactory()
        self.client.force_login(self.owner)

    def test_double_submit_creates_single_payment(self):
        url = reverse('student-payment-action', args=[self.student.id])
        data = {
            'action': 'create-payment',
            'amount': '149.90',
            'due_date': '01/07/2026',
            'method': 'pix',
        }

        first = self.client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        second = self.client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(self.student.payments.count(), 1)
