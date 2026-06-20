"""
ARQUIVO: testes do RED_FLAG forense deduplicado no RequestSecurityMiddleware.

POR QUE EXISTE:
- Ao aposentar as classes de throttle secundarias (Login/Spam, IP spoofavel +
  config morta), o unico valor delas — o audit event acionavel de breach — foi
  reaproveitado no caminho hardened (middleware), cobrindo TODOS os scopes com
  IP confiavel.
- Estes testes provam o reuso: o breach emite RED_FLAG_RATE_LIMIT, deduplicado
  por janela (cache.add) para nao amplificar escrita de auditoria sob ataque.
"""

from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.test import RequestFactory, TestCase

from shared_support.security import _emit_rate_limit_red_flag


class RateLimitRedFlagAuditTests(TestCase):

    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()

    def _req(self):
        request = self.factory.post('/login/')
        request.user = AnonymousUser()
        return request

    @patch('auditing.services.log_audit_event')
    def test_emits_red_flag_on_first_breach(self, mock_audit):
        _emit_rate_limit_red_flag(scope='login', request=self._req(), client_ip='9.9.9.9', window_seconds=60)
        self.assertEqual(mock_audit.call_count, 1)
        kwargs = mock_audit.call_args.kwargs
        self.assertEqual(kwargs['action'], 'RED_FLAG_RATE_LIMIT')
        self.assertEqual(kwargs['metadata']['scope'], 'login')
        self.assertEqual(kwargs['metadata']['ip'], '9.9.9.9')

    @patch('auditing.services.log_audit_event')
    def test_deduped_within_window_same_scope_token(self, mock_audit):
        req = self._req()
        for _ in range(3):
            _emit_rate_limit_red_flag(scope='login', request=req, client_ip='9.9.9.9', window_seconds=60)
        self.assertEqual(mock_audit.call_count, 1)  # so o 1o breach da janela audita

    @patch('auditing.services.log_audit_event')
    def test_distinct_scopes_each_emit(self, mock_audit):
        req = self._req()
        _emit_rate_limit_red_flag(scope='login', request=req, client_ip='9.9.9.9', window_seconds=60)
        _emit_rate_limit_red_flag(scope='write', request=req, client_ip='9.9.9.9', window_seconds=60)
        self.assertEqual(mock_audit.call_count, 2)

    @patch('auditing.services.log_audit_event', side_effect=RuntimeError('audit down'))
    def test_audit_failure_does_not_propagate(self, _mock):
        try:
            _emit_rate_limit_red_flag(scope='login', request=self._req(), client_ip='9.9.9.9', window_seconds=60)
        except Exception:  # noqa: BLE001
            self.fail('o RED_FLAG nao deve propagar excecao e quebrar a contencao')
