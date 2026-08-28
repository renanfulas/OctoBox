"""
ARQUIVO: teste de gate — send_student_web_push_notification contra o SDK real.

POR QUE ELE EXISTE:
- Mesma licao do bug critico da Stripe (2026-08-28, ver
  tests/test_integrations_stripe_auth.py): a fronteira com uma lib externa
  (aqui, pywebpush) nunca tinha sido exercitada contra o SDK de verdade —
  toda a feature "aula cancelada" so tem cobertura com pywebpush mockado.
- Gera um par de chaves VAPID real (py_vapid) e uma subscription_info com
  chave de cliente EC real, entao chama pywebpush.webpush() de verdade
  (sem mock) contra um endpoint inexistente — exercita construcao real do
  JWT VAPID e da criptografia do payload (onde uma mudanca de versao da
  lib mais provavelmente quebraria, igual aconteceu com stripe.dict(event)),
  sem depender de rede/push service real alcancavel.
"""

from __future__ import annotations

import base64
import os
from unittest.mock import MagicMock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.test import TestCase, override_settings
from py_vapid import Vapid02


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def _generate_vapid_private_key_pem() -> str:
    vapid = Vapid02()
    vapid.generate_keys()
    return vapid.private_pem().decode('utf-8')


def _generate_fake_subscription_info() -> dict:
    """subscription_info com o MESMO formato que um browser real devolve —
    chave publica EC do "cliente" + segredo de auth, ambos base64url sem
    padding. Endpoint aponta pra um host que nao resolve, de proposito:
    queremos exercitar a criptografia real (que roda ANTES do POST), nao
    um push service de verdade."""
    client_key = ec.generate_private_key(ec.SECP256R1())
    client_public_raw = client_key.public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    return {
        'endpoint': 'https://push.invalid.example/nao-existe-de-proposito',
        'keys': {
            'p256dh': _b64url(client_public_raw),
            'auth': _b64url(os.urandom(16)),
        },
    }


class SendStudentWebPushRealSdkTests(TestCase):
    """Sem mock de pywebpush.webpush — exercita o SDK de verdade."""

    def setUp(self):
        self.vapid_private_key_pem = _generate_vapid_private_key_pem()
        self.subscription_info = _generate_fake_subscription_info()

    def _make_fake_subscription(self):
        subscription = MagicMock()
        subscription.subscription = self.subscription_info
        subscription.identity.student_name = 'Aluno Teste'
        subscription.id = 1
        subscription.box_root_slug = 'box_test'
        subscription.endpoint = self.subscription_info['endpoint']
        return subscription

    @override_settings(
        STUDENT_WEB_PUSH_VAPID_PUBLIC_KEY='qualquer-coisa-nao-vazia',
        STUDENT_WEB_PUSH_VAPID_CLAIMS_SUBJECT='mailto:suporte@octoboxfit.com.br',
    )
    def test_real_pywebpush_call_fails_gracefully_against_unreachable_endpoint(self):
        """Endpoint nao existe -> pywebpush levanta WebPushException apos
        construir o JWT/criptografia de verdade. send_student_web_push_notification
        precisa capturar isso, marcar a falha na subscription e devolver False —
        nunca propagar (isso derrubaria o reconcile de pagamento que chama isto)."""
        from student_identity.push_notifications import send_student_web_push_notification

        with override_settings(STUDENT_WEB_PUSH_VAPID_PRIVATE_KEY=self.vapid_private_key_pem):
            subscription = self._make_fake_subscription()
            result = send_student_web_push_notification(
                subscription=subscription,
                title='Teste',
                body='Corpo de teste',
                url='/aluno/configuracoes/',
                tag='test-tag',
            )

        self.assertFalse(result)
        self.assertTrue(
            subscription.mark_push_failed.called or subscription.mark_revoked.called,
            'nem mark_push_failed nem mark_revoked foram chamados — a excecao do SDK real pode ter mudado de forma',
        )
        subscription.save.assert_called()

    @override_settings(
        STUDENT_WEB_PUSH_VAPID_PUBLIC_KEY='',
        STUDENT_WEB_PUSH_VAPID_PRIVATE_KEY='',
        STUDENT_WEB_PUSH_VAPID_CLAIMS_SUBJECT='',
    )
    def test_returns_false_without_calling_sdk_when_not_configured(self):
        from student_identity.push_notifications import send_student_web_push_notification

        subscription = self._make_fake_subscription()
        result = send_student_web_push_notification(
            subscription=subscription, title='Teste', body='Corpo', url='/x/', tag='t',
        )

        self.assertFalse(result)
        subscription.save.assert_not_called()
