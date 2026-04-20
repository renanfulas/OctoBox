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
from student_app.onboarding_state import read_pending_student_onboarding


def load_pending_student_onboarding(request):
    return read_pending_student_onboarding(request)


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


__all__ = [
    'ensure_student_onboarding_wizard_started',
    'load_pending_student_onboarding',
]
