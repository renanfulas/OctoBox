"""
ARQUIVO: testes de cenários de erro em endpoints críticos (Fase 7).

POR QUE ELE EXISTE:
- Endpoints com lógica de acesso e validação precisam de testes explícitos
  de error path, não apenas do happy path.
- Regressões de permissão (PROTECT removido, role check faltando) e de
  validação (400 virou 500) são silenciosas sem esses testes.

O QUE ESTE ARQUIVO FAZ:
1. stripe-webhook      — rejeição de assinatura inválida, idempotência, método errado.
2. api-v1-payment-link — autenticação, recurso inexistente, estado inválido.
3. api-v1-finance-freeze — autenticação, dados inválidos, recurso inexistente.
4. attendance-action   — autenticação, papel errado, presença inexistente.
5. reception-payment-action — autenticação, papel errado, recurso inexistente,
                               formulário inválido.

PONTOS CRÍTICOS:
- mock de verify_stripe_webhook isola os testes do SDK da Stripe.
- bootstrap_roles() é necessário para Group.objects.get(name=ROLE_*).
- Os testes anonimos dependem do TenantBySessionMiddleware, que intercepta
  requests nao autenticados ANTES das views e retorna 302 para /login/.
"""

import json
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.contrib.messages import get_messages
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION
from finance.models import PaymentStatus
from integrations.stripe.auth import StripeWebhookAuthError
from integrations.stripe.models import PaymentWebhookEvent
from operations.models import Attendance
from tests.factories import ClassSessionFactory, PaymentFactory, StudentFactory, UserFactory


class ErrorScenarioTests(TestCase):
    """
    Cobertura de error paths para 5 endpoints críticos do OctoBox.

    setUp cria um usuário por papel (coach, manager, reception, owner)
    mais os objetos de domínio mínimos para os testes.
    """

    def setUp(self):
        cache.clear()
        call_command('bootstrap_roles')

        self.coach = UserFactory(username='err-coach')
        self.coach.groups.add(Group.objects.get(name=ROLE_COACH))

        self.manager = UserFactory(username='err-manager')
        self.manager.groups.add(Group.objects.get(name=ROLE_MANAGER))

        self.reception = UserFactory(username='err-reception')
        self.reception.groups.add(Group.objects.get(name=ROLE_RECEPTION))

        self.owner = UserFactory(username='err-owner')
        self.owner.groups.add(Group.objects.get(name=ROLE_OWNER))

        self.student = StudentFactory()
        self.session = ClassSessionFactory()
        self.payment = PaymentFactory(student=self.student)
        self.attendance = Attendance.objects.create(
            student=self.student,
            session=self.session,
        )

    # ── 1. stripe-webhook ──────────────────────────────────────────────────

    def test_stripe_webhook_rejects_get_request(self):
        """Stripe webhook é decorado com @require_POST — GET retorna 405."""
        response = self.client.get(reverse('stripe-webhook'))
        self.assertEqual(response.status_code, 405)

    def test_stripe_webhook_returns_400_for_invalid_signature(self):
        """Payload com assinatura inválida é rejeitado com 400.

        A view deve logar o aviso e retornar 400 sem criar PaymentWebhookEvent.
        """
        with patch('finance.views.stripe_webhooks.verify_stripe_webhook') as mock_verify:
            mock_verify.side_effect = StripeWebhookAuthError('Invalid signature')
            response = self.client.post(
                reverse('stripe-webhook'),
                data=b'{}',
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='t=000,v1=fakesignature',
            )
        self.assertEqual(response.status_code, 400)

    def test_stripe_webhook_returns_200_for_duplicate_event(self):
        """Evento já processado retorna 200 (idempotência — Stripe re-envia até 200).

        O banco rejeita a segunda criação via IntegrityError (unique event_id),
        a view captura e retorna 200 com 'Duplicate event' no body.
        """
        event_id = 'evt_test_dup_fase7'
        PaymentWebhookEvent.objects.create(
            event_id=event_id,
            event_type='payment_intent.succeeded',
            payload={'id': event_id, 'type': 'payment_intent.succeeded'},
        )
        fake_event = {'id': event_id, 'type': 'payment_intent.succeeded', 'data': {}}

        with patch('finance.views.stripe_webhooks.verify_stripe_webhook', return_value=fake_event):
            response = self.client.post(
                reverse('stripe-webhook'),
                data=json.dumps(fake_event).encode(),
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='t=000,v1=irrelevant',
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Duplicate', response.content)

    # ── 2. api-v1-payment-link ─────────────────────────────────────────────

    def test_payment_link_anonymous_redirects_to_login(self):
        """PaymentLinkView exige sessão — TenantBySessionMiddleware redireciona
        o anônimo para /login/ antes de a view rodar."""
        response = self.client.get(
            reverse('api-v1-payment-link', args=[self.payment.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_payment_link_returns_404_for_nonexistent_payment(self):
        """payment_id inexistente retorna JSON 404."""
        self.client.force_login(self.owner)
        response = self.client.get(reverse('api-v1-payment-link', args=[999_999]))
        self.assertEqual(response.status_code, 404)

    def test_payment_link_returns_400_for_already_paid_payment(self):
        """Gerar link de checkout para pagamento já quitado retorna 400."""
        paid = PaymentFactory(student=self.student, status=PaymentStatus.PAID)
        self.client.force_login(self.owner)
        response = self.client.get(reverse('api-v1-payment-link', args=[paid.pk]))
        self.assertEqual(response.status_code, 400)

    # ── 3. api-v1-finance-freeze ───────────────────────────────────────────

    def test_freeze_anonymous_redirects_to_login(self):
        """StudentFreezeView exige sessão — anônimo é redirecionado para /login/."""
        response = self.client.post(
            reverse('api-v1-finance-freeze'),
            data=json.dumps({'student_id': self.student.pk, 'days': 7}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_freeze_returns_400_for_invalid_days(self):
        """days=0 é inválido — a view retorna JSON 400."""
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse('api-v1-finance-freeze'),
            data=json.dumps({'student_id': self.student.pk, 'days': 0}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_freeze_returns_404_for_nonexistent_student(self):
        """student_id inexistente retorna JSON 404."""
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse('api-v1-finance-freeze'),
            data=json.dumps({'student_id': 999_999, 'days': 7}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 404)

    # ── 4. attendance-action ───────────────────────────────────────────────

    def test_attendance_action_anonymous_redirects_to_login(self):
        """AttendanceActionView exige sessão — anônimo é redirecionado para /login/."""
        response = self.client.post(
            reverse('attendance-action', args=[self.attendance.pk, 'check-in'])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_attendance_action_returns_403_for_non_coach(self):
        """AttendanceActionView só permite COACH — MANAGER recebe 403 (PermissionDenied)."""
        self.client.force_login(self.manager)
        response = self.client.post(
            reverse('attendance-action', args=[self.attendance.pk, 'check-in'])
        )
        self.assertEqual(response.status_code, 403)

    def test_attendance_action_returns_404_for_nonexistent_attendance(self):
        """attendance_id inexistente resulta em get_object_or_404 → 404."""
        self.client.force_login(self.coach)
        response = self.client.post(
            reverse('attendance-action', args=[999_999, 'check-in'])
        )
        self.assertEqual(response.status_code, 404)

    # ── 5. reception-payment-action ────────────────────────────────────────

    def test_reception_payment_action_anonymous_redirects_to_login(self):
        """ReceptionPaymentActionView exige sessão — anônimo é redirecionado."""
        response = self.client.post(
            reverse('reception-payment-action', args=[self.payment.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_reception_payment_action_returns_403_for_coach(self):
        """ReceptionPaymentActionView permite OWNER/RECEPTION — COACH recebe 403."""
        self.client.force_login(self.coach)
        response = self.client.post(
            reverse('reception-payment-action', args=[self.payment.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_reception_payment_action_returns_404_for_nonexistent_payment(self):
        """payment_id inexistente resulta em get_object_or_404 → 404."""
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse('reception-payment-action', args=[999_999])
        )
        self.assertEqual(response.status_code, 404)

    def test_reception_payment_action_invalid_form_redirects_with_error_message(self):
        """POST com formulário inválido redireciona (302) e adiciona mensagem de erro.

        Garante que a falha de validação não produz 500 nem silencia o erro —
        o usuário deve ver feedback claro no balcão.
        """
        self.client.force_login(self.reception)
        response = self.client.post(
            reverse('reception-payment-action', args=[self.payment.pk]),
            data={},  # vazio — payment_id, action, due_date e method são required
        )

        self.assertEqual(response.status_code, 302)

        flash_messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(
            any('nao foi aplicada' in msg for msg in flash_messages),
            msg=f'Mensagem de erro esperada não encontrada. Mensagens presentes: {flash_messages}',
        )
