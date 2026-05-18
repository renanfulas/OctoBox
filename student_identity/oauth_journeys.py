"""
ARQUIVO: jornadas especiais do callback OAuth do app do aluno.

POR QUE ELE EXISTE:
- separa da view o tratamento das jornadas que desviam do login direto para home ou pendencia.

O QUE ESTE ARQUIVO FAZ:
1. resolve a jornada a partir do invite token.
2. trata link em massa do box.
3. trata convite individual de lead importado.
4. registra eventos do funil ligados a cada jornada.

PONTOS CRITICOS:
- qualquer mudanca aqui altera a decisao entre onboarding reduzido, onboarding em massa e entrada direta no app.
- os eventos de auditoria do funil precisam continuar identicos ao fluxo anterior.
"""

from __future__ import annotations

from django.shortcuts import redirect

# Sprint 4: get_box_runtime_slug import removido — verificacao slug-vs-runtime
# era estruturalmente quebrada em schema-per-tenant (ver comentario abaixo).
from student_app.onboarding_state import store_pending_student_onboarding

from .funnel_events import record_student_onboarding_event
from .infrastructure.session import attach_student_session_cookie
from .models import StudentOnboardingJourney
from .security import build_student_device_fingerprint


def resolve_student_oauth_journey(*, repository, invite_token: str) -> str:
    if not invite_token:
        return ''
    box_invite_link = repository.find_box_invite_link_by_token(invite_token)
    if box_invite_link is not None:
        return StudentOnboardingJourney.MASS_BOX_INVITE
    invitation = repository.find_invitation_by_token(invite_token)
    if invitation is not None:
        return invitation.onboarding_journey
    return ''


def handle_student_special_oauth_journey(
    *,
    request,
    provider: str,
    identity_payload,
    state_payload: dict,
    result,
    repository,
):
    invite_token = (state_payload.get('invite_token') or '').strip()
    if not invite_token:
        return None

    box_invite_link = repository.find_box_invite_link_by_token(invite_token)
    if box_invite_link is not None:
        # Sprint 4 schema-per-tenant: OAuth callback runs em public schema
        # (/aluno/auth/ esta em PUBLIC_SCHEMA_PATHS). get_box_runtime_slug()
        # retorna 'control' aqui (fallback env), enquanto link.box_root_slug
        # foi salvo como nome do schema do tenant (ex.: 'box_endorfina') no
        # momento da criacao do link dentro do contexto do owner.
        # A verificacao slug-vs-runtime que existia aqui ficou estruturalmente
        # quebrada: o link e a fonte de verdade do box-alvo. Manter so o gate
        # de "link ainda aceita usos".
        if not box_invite_link.can_accept:
            return _redirect_with_message(request, 'error', 'Este link em massa nao esta mais disponivel para novos cadastros.')
        # Sprint 4: ativar o tenant do link como contexto ativo para que
        # operacoes tenant-aware downstream (AuditEvent, ContentType, etc.)
        # encontrem suas tabelas no schema correto. /aluno/auth/ esta em
        # PUBLIC_SCHEMA_PATHS, entao o TenantBySessionMiddleware setou public
        # — precisamos sobrescrever aqui agora que sabemos o box alvo.
        _activate_box_tenant(box_invite_link.box_id, box_root_slug=box_invite_link.box_root_slug)
        if result.success and result.identity is not None:
            response = redirect('student-app-home')
            attach_student_session_cookie(
                response,
                identity_id=result.identity.id,
                box_root_slug=result.identity.box_root_slug,
                device_fingerprint=build_student_device_fingerprint(request),
            )
            return response
        repository.record_box_invite_acceptance(box_invite_link)
        payload = {
            'journey': StudentOnboardingJourney.MASS_BOX_INVITE,
            'box_root_slug': box_invite_link.box_root_slug,
            'box_id': box_invite_link.box_id,
            'provider': identity_payload.provider,
            'provider_subject': identity_payload.provider_subject,
            'email': identity_payload.email,
            'box_invite_link_id': box_invite_link.id,
            'box_invite_link_token': str(box_invite_link.token),
        }
        if not payload['box_root_slug'] or not payload['provider'] or not payload['provider_subject']:
            return _redirect_with_message(request, 'warning', 'Sua sessão de cadastro não ficou completa. Tente entrar novamente.')
        store_pending_student_onboarding(request, payload=payload)
        record_student_onboarding_event(
            actor=None,
            actor_role='',
            journey=StudentOnboardingJourney.MASS_BOX_INVITE,
            event='oauth_completed',
            target_model='student_identity.StudentBoxInviteLink',
            target_id=str(box_invite_link.id),
            target_label=box_invite_link.box_root_slug,
            description='OAuth concluido para link em massa do box.',
            metadata={
                'box_root_slug': box_invite_link.box_root_slug,
                'box_invite_link_id': box_invite_link.id,
                'provider': provider,
            },
        )
        return redirect('student-app-onboarding')

    invitation = repository.find_invitation_by_token(invite_token)
    if invitation is None or not result.success or result.identity is None:
        return None
    if invitation.onboarding_journey != StudentOnboardingJourney.IMPORTED_LEAD_INVITE:
        return None

    # Sprint 4: ativar tenant do convite (ver comentario em box_invite_link acima).
    _activate_box_tenant(invitation.box_id, box_root_slug=invitation.box_root_slug)

    attach_response = redirect('student-app-onboarding')
    attach_student_session_cookie(
        attach_response,
        identity_id=result.identity.id,
        box_root_slug=result.identity.box_root_slug,
        device_fingerprint=build_student_device_fingerprint(request),
    )
    payload = {
        'journey': invitation.onboarding_journey,
        'box_root_slug': invitation.box_root_slug,
        'box_id': invitation.box_id,
        'identity_id': result.identity.id,
        'student_id': result.identity.student_id,
        'invitation_id': invitation.id,
        'provider': identity_payload.provider,
        'provider_subject': identity_payload.provider_subject,
        'email': identity_payload.email,
    }
    if not payload['box_root_slug'] or not payload['identity_id'] or not payload['student_id']:
        return _redirect_with_message(request, 'warning', 'Sua sessão de cadastro não ficou completa. Tente entrar novamente.')
    store_pending_student_onboarding(request, payload=payload)
    record_student_onboarding_event(
        actor=None,
        actor_role='',
        journey=invitation.onboarding_journey,
        event='oauth_completed',
        target_model='student_identity.StudentAppInvitation',
        target_id=str(invitation.id),
        target_label=invitation.student_name,  # # Sprint 2: denorm
        description='OAuth concluido para convite individual do onboarding do aluno.',
        metadata={
            'box_root_slug': invitation.box_root_slug,
            'student_id': invitation.student_id,
            'identity_id': result.identity.id,
            'invitation_id': invitation.id,
            'provider': provider,
        },
    )
    return attach_response


def record_student_entry_completed_journey(*, provider: str, result, journey: str):
    if not journey:
        return

    record_student_onboarding_event(
        actor=None,
        actor_role='',
        journey=journey,
        event='oauth_completed',
        target_model='student_identity.StudentIdentity',
        target_id=str(result.identity.id),
        target_label=result.identity.student_name,
        description='OAuth concluido com sucesso no onboarding do aluno.',
        metadata={
            'box_root_slug': result.identity.box_root_slug,
            'identity_id': result.identity.id,
            'student_id': result.identity.student_id,
            'provider': provider,
        },
    )
    record_student_onboarding_event(
        actor=None,
        actor_role='',
        journey=journey,
        event='app_entry_completed',
        target_model='student_identity.StudentIdentity',
        target_id=str(result.identity.id),
        target_label=result.identity.student_name,
        description='Entrada direta no app concluida via convite do aluno.',
        metadata={
            'box_root_slug': result.identity.box_root_slug,
            'identity_id': result.identity.id,
            'student_id': result.identity.student_id,
            'provider': provider,
        },
    )


def _redirect_with_message(request, level: str, message: str):
    from django.contrib import messages

    getattr(messages, level)(request, message)
    return redirect('student-identity-login')


def _activate_box_tenant(box_id=None, *, box_root_slug: str = '') -> None:
    """Sprint 4 schema-per-tenant: ativa o tenant identificado pelo box.

    O OAuth callback corre em public schema (rota /aluno/auth/ esta em
    PUBLIC_SCHEMA_PATHS). Apos descobrir o box-alvo via link ou convite,
    precisamos sobrescrever o schema para tenant para que operacoes
    tenant-aware (AuditEvent em boxcore_auditevent, etc.) encontrem as
    tabelas no schema correto.

    Aceita box_id (caminho preferido) ou box_root_slug (fallback para legado
    onde a FK control.Box ainda nao tinha sido populada). box_root_slug
    historicamente armazena o schema_name do tenant.

    Falha silenciosamente se nenhum dos dois resolve um Box ATIVO — o caller
    continua em public (downstream pode falhar mas com erros mais explicitos).
    """
    if not box_id and not box_root_slug:
        return
    try:
        from control.models import Box
        from django.db import connection
        if box_id:
            box = Box.objects.get(pk=box_id, status=Box.Status.ACTIVE)
        else:
            box = Box.objects.get(schema_name=box_root_slug, status=Box.Status.ACTIVE)
        connection.set_tenant(box)
    except Exception:
        # Logging seria ideal mas evita explodir o callback em edge cases.
        # Se o box nao puder ser ativado, downstream falhara com erros mais
        # explicitos (table-not-found) que ja sao auto-explicativos.
        pass


__all__ = [
    'handle_student_special_oauth_journey',
    'record_student_entry_completed_journey',
    'resolve_student_oauth_journey',
]
