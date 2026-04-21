"""
ARQUIVO: loader do wizard de onboarding do aluno.

POR QUE ELE EXISTE:
- separa da view a leitura do onboarding pendente e o registro de entrada no wizard.

O QUE ESTE ARQUIVO FAZ:
1. le onboarding pendente da sessao.
2. registra o evento de inicio do wizard uma unica vez.
3. persiste o marcador de wizard iniciado na sessao.

PONTOS CRITICOS:
- manter idempotencia do evento `wizard_started`.
- preservar o contrato da sessao `student_pending_onboarding`.
"""

from shared_support.box_runtime import get_box_runtime_slug
from student_identity.funnel_events import record_student_onboarding_event
from student_identity.models import StudentAppInvitation, StudentBoxInviteLink, StudentIdentity, StudentOnboardingJourney
from student_app.onboarding_state import read_pending_student_onboarding


def load_pending_student_onboarding(request):
    pending_onboarding = read_pending_student_onboarding(request)
    if pending_onboarding is None:
        return None
    return pending_onboarding if _is_valid_pending_student_onboarding(pending_onboarding) else None


def ensure_student_onboarding_wizard_started(*, request, pending_onboarding):
    if pending_onboarding.get('wizard_started_recorded'):
        return pending_onboarding
    record_student_onboarding_event(
        actor=None,
        actor_role='',
        journey=pending_onboarding.get('journey', ''),
        event='wizard_started',
        target_model='student_app.StudentOnboardingWizard',
        target_label=pending_onboarding.get('journey', ''),
        description='Wizard do onboarding do aluno iniciado.',
        metadata={
            'box_root_slug': pending_onboarding.get('box_root_slug') or get_box_runtime_slug(),
            'student_id': pending_onboarding.get('student_id'),
            'identity_id': pending_onboarding.get('identity_id'),
            'invitation_id': pending_onboarding.get('invitation_id'),
            'box_invite_link_id': pending_onboarding.get('box_invite_link_id'),
        },
    )
    pending_onboarding['wizard_started_recorded'] = True
    store = request.session.get('student_pending_onboarding') or {}
    store.update(pending_onboarding)
    request.session['student_pending_onboarding'] = store
    request.session.modified = True
    return pending_onboarding


def _is_valid_pending_student_onboarding(pending_onboarding) -> bool:
    journey = (pending_onboarding.get('journey') or '').strip()
    if not journey:
        return False
    box_root_slug = (pending_onboarding.get('box_root_slug') or '').strip()
    if not box_root_slug:
        return False
    if journey == StudentOnboardingJourney.MASS_BOX_INVITE:
        if not all(
            (pending_onboarding.get(field) or '').strip()
            for field in ('provider', 'provider_subject')
        ):
            return False
        box_invite_link_id = pending_onboarding.get('box_invite_link_id')
        if not box_invite_link_id:
            return True
        box_invite_link = StudentBoxInviteLink.objects.filter(pk=box_invite_link_id).first()
        return bool(box_invite_link and box_invite_link.box_root_slug == box_root_slug)
    if journey == StudentOnboardingJourney.IMPORTED_LEAD_INVITE:
        identity_id = pending_onboarding.get('identity_id')
        student_id = pending_onboarding.get('student_id')
        invitation_id = pending_onboarding.get('invitation_id')
        if not identity_id or not student_id:
            return False
        identity = StudentIdentity.objects.select_related('student').filter(pk=identity_id).first()
        if identity is None or identity.student_id != student_id or identity.box_root_slug != box_root_slug:
            return False
        if invitation_id:
            invitation = StudentAppInvitation.objects.filter(pk=invitation_id).first()
            if invitation is None or invitation.student_id != student_id or invitation.box_root_slug != box_root_slug:
                return False
        return True
    return True


__all__ = [
    'ensure_student_onboarding_wizard_started',
    'load_pending_student_onboarding',
]
