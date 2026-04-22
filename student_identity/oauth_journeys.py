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

from shared_support.box_runtime import get_box_runtime_slug
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
        if box_invite_link.box_root_slug != get_box_runtime_slug():
            return _redirect_with_message(request, 'error', 'Este link em massa nao pertence ao box atual.')
        if not box_invite_link.can_accept:
            return _redirect_with_message(request, 'error', 'Este link em massa nao esta mais disponivel para novos cadastros.')
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
            'provider': identity_payload.provider,
            'provider_subject': identity_payload.provider_subject,
            'email': identity_payload.email,
            'box_invite_link_id': box_invite_link.id,
            'box_invite_link_token': str(box_invite_link.token),
        }
        if not payload['box_root_slug'] or not payload['provider'] or not payload['provider_subject']:
            return _redirect_with_message(request, 'warning', 'Sua sessao de cadastro nao ficou completa. Tente entrar novamente.')
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
        'identity_id': result.identity.id,
        'student_id': result.identity.student_id,
        'invitation_id': invitation.id,
        'provider': identity_payload.provider,
        'provider_subject': identity_payload.provider_subject,
        'email': identity_payload.email,
    }
    if not payload['box_root_slug'] or not payload['identity_id'] or not payload['student_id']:
        return _redirect_with_message(request, 'warning', 'Sua sessao de cadastro nao ficou completa. Tente entrar novamente.')
    store_pending_student_onboarding(request, payload=payload)
    record_student_onboarding_event(
        actor=None,
        actor_role='',
        journey=invitation.onboarding_journey,
        event='oauth_completed',
        target_model='student_identity.StudentAppInvitation',
        target_id=str(invitation.id),
        target_label=invitation.student.full_name,
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


__all__ = [
    'handle_student_special_oauth_journey',
    'record_student_entry_completed_journey',
    'resolve_student_oauth_journey',
]
