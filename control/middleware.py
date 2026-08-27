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

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.db import connection
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django_tenants.utils import get_public_schema_name

logger = logging.getLogger('control.middleware')

# Nome do atributo em request.user onde o Membership do box ativo fica anexado
# (setado em TenantBySessionMiddleware._resolve_box). access.roles.get_user_role
# lê este atributo para resolver papel POR BOX. Constante compartilhada em vez
# de string mágica duplicada — control é SHARED_APP e carrega antes de access
# (TENANT_APP), então a dependência access -> control é segura (sem circular).
OCTOBOX_MEMBERSHIP_REQUEST_ATTR = '_octobox_membership'

# Paths que NUNCA devem entrar em tenant — ficam em public schema.
# Qualquer URL que precisa funcionar antes de um Box existir vai aqui.
PUBLIC_SCHEMA_PATHS = (
    # Literal '/admin/' (nao settings.ADMIN_URL_PATH): safety net para o path
    # default 404ar naturalmente quando o admin real esta em outro lugar
    # (obscuridade de seguranca via DJANGO_ADMIN_URL_PATH). O path REAL do
    # admin (settings.ADMIN_URL_PATH) NAO entra aqui — ver _is_admin_path().
    # Torna-lo sempre-publico incondicionalmente (como uma correcao anterior
    # tentou) quebra admin actions em modelos tenant-scoped (ex.: editar
    # Payment): a requisicao nunca chega a resolver o Box do usuario, entao
    # roda contra o schema errado ("relation nao existe"). O caminho certo
    # para "superuser sem Box ainda" e o fallback em __call__ (box is None),
    # nao um bypass cego de toda a subarvore do admin.
    '/admin/',
    '/signup/',
    '/financeiro/stripe/webhook/',
    # Captura segura de origem declarada — link externo para alunos (anon)
    # registrarem origem via token assinado. Sem isso, POST anonimo cai em
    # 302→/login/ antes da view validar o token.
    '/alunos/origem/qualificar/',
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
    # Fluxo Early Adopter: checkout publico para novos boxes. Anonimos chegam
    # via CTA da landing (/checkout/?plan=...). Sem isso o middleware bloqueia
    # com redirect para /login/ e o ?plan= se perde, quebrando o funil.
    '/checkout/',
    '/onboarding/',
    # Seletor de box para staff multi-box (ex.: superdev). Roda em public porque
    # o usuario ainda nao tem tenant resolvido ao escolher a box. Sem isso, o
    # proprio /box/ cairia na resolucao de tenant e poderia redirecionar em loop.
    '/box/',
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

# Paths que sao publicos APENAS em correspondencia EXATA (sem subpaths).
# Diferente de PUBLIC_SCHEMA_PATHS (que usa startswith), aqui validamos
# path == prefix. Usado para endpoints de manifesto/discovery onde o
# pai e publico mas filhos sao privados (ex.: /api/ expoe versoes
# disponiveis; /api/v1/finance/... e autenticado e exige tenant).
PUBLIC_SCHEMA_EXACT_PATHS = (
    # Home marketing landing (host www.octoboxfit.com.br). Anonimo precisa ver
    # a pagina; usuario logado vai pra /dashboard/ (decidido na view). Sem
    # exact-match, qualquer subpath caia em /login/.
    '/',
    # Pagina de produto (vitrine publica). Anonimo precisa ver sem fazer login.
    '/produto/',
    '/api/',
    '/api/v1/',
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
            # Save/restore: paths publicos forçam public DURANTE o request
            # (proteção C1), mas a connection volta ao estado anterior
            # APOS o request. Sem isso, um request a /admin/ (público)
            # deixa a connection em public, e o próximo request reusado
            # na mesma connection começa com search_path errado. Em prod
            # isso e mitigado por CONN_MAX_AGE/pool, mas em testes (e em
            # cenarios de assertRedirects que disparam segunda Client.get)
            # o efeito vaza entre requests do mesmo teste.
            _previous_tenant = getattr(connection, 'tenant', None)
            self._set_public(request)
            try:
                return self.get_response(request)
            finally:
                if _previous_tenant is not None:
                    try:
                        connection.set_tenant(_previous_tenant)
                    except Exception:
                        connection.set_schema_to_public()

        if not request.user.is_authenticated:
            # Usuário anônimo em path privado → login
            login_url = '/login/'
            return redirect(f'{login_url}?{REDIRECT_FIELD_NAME}={request.path}')

        box = self._resolve_box(request)
        if box is None:
            self._set_public(request)
            # Sem box ativo resolvido. Se o usuario tem vinculos (ou e superuser),
            # mandar para o seletor de box em vez de 403 seco. Caso tipico do
            # superdev (Membership em todo box, mas is_primary_box=False) e de
            # owners multi-box sem primary definido. /box/ e public (sem tenant),
            # entao nao ha risco de loop de redirect.
            from control.models import Membership

            has_membership = Membership.objects.filter(user=request.user).exists()
            if request.user.is_superuser and self._is_admin_path(request.path):
                # Superuser sem NENHUM Box/Membership ainda (primeiro acesso
                # administrativo do ambiente, ex.: bootstrap inicial) —
                # deixa entrar no admin hardened em public schema em vez de
                # mandar pro seletor de box vazio (dead-end sem 403 nem erro
                # explicito). Bug original corrigido no commit ad20277.
                return self.get_response(request)
            if has_membership or request.user.is_superuser:
                return redirect(f'/box/?{REDIRECT_FIELD_NAME}={request.path}')

            logger.warning(
                'TenantBySessionMiddleware: user=%s sem Box resolvido para path=%s',
                request.user.pk,
                request.path,
            )
            return HttpResponseForbidden('Nenhum box associado a este usuário.')

        # Onda 1c: expõe o Membership do box ativo em request.user para
        # access.roles.get_user_role resolver papel POR BOX. NUNCA thread-local
        # (vazaria entre requests/usuários no mesmo worker em runtime síncrono)
        # — o atributo vive só na instância deste request.user, que morre com
        # o request.
        setattr(
            request.user,
            OCTOBOX_MEMBERSHIP_REQUEST_ATTR,
            getattr(request, '_resolved_membership', None),
        )

        # Setar tenant — django-tenants emite SET search_path TO box_xxx, public
        connection.set_tenant(box)
        request.tenant = box

        response = self.get_response(request)
        return response

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _is_public_path(self, path: str) -> bool:
        if any(path.startswith(prefix) for prefix in PUBLIC_SCHEMA_PATHS):
            return True
        return path in PUBLIC_SCHEMA_EXACT_PATHS

    def _is_admin_path(self, path: str) -> bool:
        """settings.ADMIN_URL_PATH e customizavel via DJANGO_ADMIN_URL_PATH
        (obscuridade de seguranca em producao, ex.: 'painel-<hash>/'). Lido em
        tempo de chamada (nao congelado em import time) — override_settings
        em teste precisa refletir aqui.

        Deliberadamente SEPARADO de _is_public_path: o admin so deve ignorar
        a resolucao normal de tenant quando o usuario nao tem Box nenhum
        ainda (ver __call__, ramo `box is None`) — nao sempre. Uma correcao
        anterior (2026-08-27, commit ad20277) tratava a subarvore inteira do
        admin como sempre-publica incondicionalmente, o que quebrava admin
        actions em modelos tenant-scoped (ex.: editar Payment): a requisicao
        nunca chegava a resolver o Box do usuario, rodava contra o schema
        errado ("relation nao existe").
        """
        return path.startswith(f'/{settings.ADMIN_URL_PATH}')

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

        Efeito colateral: anexa o Membership resolvido em
        request._resolved_membership. __call__ o expõe em request.user logo
        depois (ver OCTOBOX_MEMBERSHIP_REQUEST_ATTR) para get_user_role
        resolver papel por box sem query adicional — o Membership já foi
        buscado aqui de qualquer forma.
        """
        from control.models import Box, Membership  # import local para evitar circular no boot

        active_box_id = request.session.get('active_box_id')
        if active_box_id:
            try:
                box = Box.objects.get(pk=active_box_id, status=Box.Status.ACTIVE)
                # C1c: .first() em vez de .exists() — o Membership (com o role
                # do box ativo) já estava sendo buscado e descartado aqui.
                membership = Membership.objects.filter(user=request.user, box=box).first()
                if membership is not None:
                    request._resolved_membership = membership
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
                request._resolved_membership = membership
                return membership.box
        except Exception:
            logger.exception('Erro ao resolver Membership para user=%s', request.user.pk)

        return None
