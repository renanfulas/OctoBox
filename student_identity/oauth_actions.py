"""
ARQUIVO: actions do callback OAuth do app do aluno.

POR QUE ELE EXISTE:
- separa da view a troca do code, a autenticacao da identidade e a finalizacao da sessao do aluno.

O QUE ESTE ARQUIVO FAZ:
1. troca o authorization code pelo payload de identidade do provedor.
2. autentica ou recupera a identidade do aluno no box atual.
3. trata jornadas especiais antes da entrada direta no app.
4. finaliza sessao, mensagens e alertas de anomalia do login bem-sucedido.

PONTOS CRITICOS:
- qualquer mudanca aqui altera redirect, cookie de sessao, membership pending e alertas de seguranca.
- a action precisa preservar o comportamento do callback antes de qualquer refinamento interno.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect

from .models import StudentBoxMembership, StudentBoxMembershipStatus
from .oauth_journeys import (
    handle_student_special_oauth_journey,
    record_student_entry_completed_journey,
    resolve_student_oauth_journey,
)
from .oauth_providers import OAuthProviderError
from .security import (
    build_student_device_fingerprint,
    check_student_flow_rate_limit,
    maybe_emit_student_anomaly_alert,
    resolve_student_client_ip,
)


class StudentOAuthProviderExchangeError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class StudentOAuthExchangeResult:
    identity_payload: object
    authentication_result: object


def exchange_student_oauth_identity_payload(*, provider: str, code: str, request, provider_builder):
    try:
        oauth_provider = provider_builder(provider)
        return oauth_provider.exchange_code(code=code, request=request)
    except OAuthProviderError as exc:
        raise StudentOAuthProviderExchangeError(str(exc)) from exc


def authenticate_student_oauth_identity(*, authenticate_identity, identity_payload, invite_token: str):
    return authenticate_identity(
        provider_name=identity_payload.provider,
        email=identity_payload.email,
        provider_subject=identity_payload.provider_subject,
        invite_token=invite_token,
    )


def finalize_student_oauth_callback(
    *,
    request,
    provider: str,
    state_payload: dict,
    identity_payload,
    authentication_result,
    identity_repository_class,
    map_failure_reason,
):
    repository = identity_repository_class()
    redirect_response = handle_student_special_oauth_journey(
        request=request,
        provider=provider,
        identity_payload=identity_payload,
        state_payload=state_payload,
        result=authentication_result,
        repository=repository,
    )
    if redirect_response is not None:
        return redirect_response

    if not authentication_result.success or authentication_result.identity is None:
        messages.error(request, map_failure_reason(authentication_result.failure_reason))
        redirect_url = 'student-identity-login'
        invite_token = (state_payload.get('invite_token') or '').strip()
        if invite_token:
            return redirect(f"/aluno/auth/login/?invite={invite_token}")
        return redirect(redirect_url)

    active_membership = StudentBoxMembership.objects.filter(
        identity_id=authentication_result.identity.id,
        box_root_slug=authentication_result.identity.box_root_slug,
    ).first()
    redirect_name = 'student-app-home'
    if active_membership is not None and active_membership.status == StudentBoxMembershipStatus.PENDING_APPROVAL:
        redirect_name = 'student-app-membership-pending'
        messages.info(request, 'Sua identidade foi validada. Agora o box precisa aprovar este acesso.')

    response = redirect(redirect_name)
    _attach_student_session(
        request=request,
        response=response,
        authentication_result=authentication_result,
    )
    _emit_student_oauth_anomaly_alerts(
        request=request,
        provider=provider,
        authentication_result=authentication_result,
    )
    if redirect_name == 'student-app-home':
        journey = resolve_student_oauth_journey(
            repository=repository,
            invite_token=(state_payload.get('invite_token') or '').strip(),
        )
        record_student_entry_completed_journey(
            provider=provider,
            result=authentication_result,
            journey=journey,
        )
        messages.success(request, f'Acesso do aluno {authentication_result.identity.student_name} confirmado.')
    return response


def _attach_student_session(*, request, response, authentication_result):
    from .infrastructure.session import attach_student_session_cookie

    attach_student_session_cookie(
        response,
        identity_id=authentication_result.identity.id,
        box_root_slug=authentication_result.identity.box_root_slug,
        device_fingerprint=build_student_device_fingerprint(request),
    )


def _emit_student_oauth_anomaly_alerts(*, request, provider: str, authentication_result):
    client_ip = resolve_student_client_ip(request)
    actor_label = authentication_result.identity.student_name
    ip_anomaly_allowed, _ = check_student_flow_rate_limit(
        scope='student-invite-accept-ip-alert',
        token=f'ip:{client_ip}',
        limit=max(1, int(getattr(settings, 'STUDENT_INVITE_ACCEPT_IP_ALERT_THRESHOLD', 8))),
        window_seconds=max(1, int(getattr(settings, 'STUDENT_INVITE_ACCEPT_IP_ALERT_WINDOW_SECONDS', 600))),
    )
    if not ip_anomaly_allowed:
        maybe_emit_student_anomaly_alert(
            scope='student-invite-accept-ip',
            actor=None,
            actor_role='',
            target_label=client_ip,
            description='Volume suspeito de aceite de invite/callback social vindo do mesmo IP.',
            metadata={
                'box_root_slug': authentication_result.identity.box_root_slug,
                'student_identity_id': authentication_result.identity.id,
                'provider': provider,
            },
            dedupe_window_seconds=max(60, int(getattr(settings, 'STUDENT_INVITE_ACCEPT_IP_ALERT_WINDOW_SECONDS', 600))),
        )
    box_anomaly_allowed, _ = check_student_flow_rate_limit(
        scope='student-invite-accept-box-alert',
        token=f'box:{authentication_result.identity.box_root_slug}',
        limit=max(1, int(getattr(settings, 'STUDENT_INVITE_ACCEPT_BOX_ALERT_THRESHOLD', 12))),
        window_seconds=max(1, int(getattr(settings, 'STUDENT_INVITE_ACCEPT_BOX_ALERT_WINDOW_SECONDS', 600))),
    )
    if not box_anomaly_allowed:
        maybe_emit_student_anomaly_alert(
            scope='student-invite-accept-box',
            actor=None,
            actor_role='',
            target_label=authentication_result.identity.box_root_slug,
            description='Volume suspeito de aceite de invites concentrado no mesmo box em janela curta.',
            metadata={
                'client_ip': client_ip,
                'student_identity_id': authentication_result.identity.id,
                'student_name': actor_label,
                'provider': provider,
            },
            dedupe_window_seconds=max(60, int(getattr(settings, 'STUDENT_INVITE_ACCEPT_BOX_ALERT_WINDOW_SECONDS', 600))),
        )


__all__ = [
    'StudentOAuthProviderExchangeError',
    'authenticate_student_oauth_identity',
    'exchange_student_oauth_identity_payload',
    'finalize_student_oauth_callback',
]
