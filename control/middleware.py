"""
ARQUIVO: middleware de identificação de tenant por sessão.

POR QUE ELE EXISTE:
- Implementa a decisão §1 travada: tenant identification session-based na Fase 1.
- Substitui o BOX_RUNTIME_SLUG estático por resolução dinâmica por request.

O QUE ESTE ARQUIVO FAZ:
1. Para paths em PUBLIC_SCHEMA_PATHS: seta schema para public (C1 fix — reset explícito).
2. Para usuário autenticado: resolve Box via session['active_box_id'] ou Membership.is_primary_box.
3. Para usuário anônimo em path privado: redirect para login.
4. Sempre chama connection.set_tenant() ou connection.set_schema_to_public() (nunca deixa search_path herdado).

PONTOS CRITICOS (Tier-1 C1 fix):
- Toda execução deste middleware termina com search_path explícito.
- Mesmo em paths públicos, set_schema_to_public() é chamado para garantir reset.
- Protege contra herança de search_path de conexão reutilizada (CONN_MAX_AGE > 0).

CONTRATO:
- Input:  request com session iniciada (SessionMiddleware já rodou).
- Output: connection.tenant setado OU connection em public.
- Exceções documentadas nos comentários inline.
"""

from __future__ import annotations

import logging

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.db import connection
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django_tenants.utils import get_public_schema_name

logger = logging.getLogger('control.middleware')

# Paths que NUNCA devem entrar em tenant — ficam em public schema.
# Qualquer URL que precisa funcionar antes de um Box existir vai aqui.
PUBLIC_SCHEMA_PATHS = (
    '/admin/',
    '/signup/',
    '/financeiro/stripe/webhook/',
    '/api/v1/health/',
    # Webhooks de integracoes externas (Resend, WhatsApp). Recebem POST
    # de servicos terceiros que NAO tem session/auth. View interna
    # valida assinatura HMAC. Sem isso, TenantBySessionMiddleware
    # redireciona o POST anonimo para /login/ (302) antes da view
    # validar a assinatura — quebra contrato de webhook (esperado 400
    # para assinatura invalida).
    '/api/v1/integrations/',
    '/login/',
    '/logout/',
    '/onboarding/',
    # Sprint 4: TODO o app do aluno bypassa o staff tenant middleware.
    # StudentAuthMiddleware (mais abaixo na chain) faz a auth via cookie
    # proprio do aluno e resolve o tenant via session_payload.box_id.
    # Sem isso, TenantBySessionMiddleware redirecionaria alunos anonimos
    # para /login/ (staff) antes do StudentAuthMiddleware rodar.
    '/aluno/',
    # PWA publica de workouts: rotas /renan/<slug> e /renan/<slug>/sw.js
    # sao paginas estaticas-ish acessadas SEM login (PWA pessoal por aluno).
    # Sem isso, TenantBySessionMiddleware redireciona anonimo para /login/.
    '/renan/',
    '/static/',
    '/favicon.ico',
    '/__debug__/',            # django-debug-toolbar
)


class TenantBySessionMiddleware:
    """
    Resolve tenant por sessão Django (staff).

    Ordem de resolução:
    1. Path público → public schema (sem tenant).
    2. request.session['active_box_id'] → Box por PK.
    3. User.memberships.filter(is_primary_box=True).first() → Box primário.
    4. Sem Box → 403.
    5. User anônimo em path privado → redirect login.

    Idempotência: chamar duas vezes no mesmo request é equivalente ao último valor.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # C1 FIX: sempre resetar search_path explicitamente neste middleware.
        # Nunca confiar no search_path herdado de conexão reutilizada.
        if self._is_public_path(request.path):
            self._set_public(request)
            return self.get_response(request)

        if not request.user.is_authenticated:
            # Usuário anônimo em path privado → login
            login_url = '/login/'
            return redirect(f'{login_url}?{REDIRECT_FIELD_NAME}={request.path}')

        box = self._resolve_box(request)
        if box is None:
            logger.warning(
                'TenantBySessionMiddleware: user=%s sem Box resolvido para path=%s',
                request.user.pk,
                request.path,
            )
            self._set_public(request)
            return HttpResponseForbidden('Nenhum box associado a este usuário.')

        # Setar tenant — django-tenants emite SET search_path TO box_xxx, public
        connection.set_tenant(box)
        request.tenant = box

        response = self.get_response(request)
        return response

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _is_public_path(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in PUBLIC_SCHEMA_PATHS)

    def _set_public(self, request) -> None:
        """Reset explícito para public schema. Corrige herança de search_path (C1)."""
        connection.set_schema_to_public()
        request.tenant = None

    def _resolve_box(self, request) -> 'Box | None':
        """
        Resolve o Box ativo para este request.

        Prioridade:
        1. session['active_box_id'] — set pelo /box/switch/ ou pelo onboarding.
        2. Membership.is_primary_box=True — padrão após login.
        """
        from control.models import Box, Membership  # import local para evitar circular no boot

        active_box_id = request.session.get('active_box_id')
        if active_box_id:
            try:
                box = Box.objects.get(pk=active_box_id, status=Box.Status.ACTIVE)
                # Confirmar que o user ainda tem Membership neste box
                if Membership.objects.filter(user=request.user, box=box).exists():
                    return box
                else:
                    # Box na session mas user não tem mais Membership → limpar session
                    logger.warning(
                        'active_box_id=%s na session mas user=%s sem Membership — limpando.',
                        active_box_id, request.user.pk,
                    )
                    del request.session['active_box_id']
            except Box.DoesNotExist:
                del request.session['active_box_id']

        # Fallback: primary box do user
        try:
            membership = (
                Membership.objects
                .select_related('box')
                .filter(user=request.user, is_primary_box=True, box__status=Box.Status.ACTIVE)
                .first()
            )
            if membership:
                # Setar na session para próximos requests (evita query a cada request)
                request.session['active_box_id'] = membership.box_id
                return membership.box
        except Exception:
            logger.exception('Erro ao resolver Membership para user=%s', request.user.pk)

        return None
