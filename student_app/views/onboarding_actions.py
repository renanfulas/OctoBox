"""
ARQUIVO: actions de conclusao do wizard de onboarding.

POR QUE ELE EXISTE:
- separa da view a conclusao das jornadas do onboarding do aluno.

O QUE ESTE ARQUIVO FAZ:
1. conclui onboarding em massa.
2. conclui onboarding de lead importado.
3. aplica redirects, cookie e mensagens finais.

PONTOS CRITICOS:
- manter side effects, cookie e mensagens identicos ao fluxo anterior.
- a decisao de qual action chamar continua pequena e explicita na view.
"""

from django.contrib import messages
from django.shortcuts import redirect

from student_identity.infrastructure.session import attach_student_session_cookie
from student_identity.security import build_student_device_fingerprint
from student_identity.models import StudentOnboardingJourney
from student_app.onboarding_state import clear_pending_student_onboarding


def complete_student_mass_onboarding(view, form):
    result = view._get_onboarding_workflow().complete_mass_onboarding(
        pending_onboarding=view.pending_onboarding,
        cleaned_data=form.cleaned_data,
    )
    clear_pending_student_onboarding(view.request)
    response = redirect('student-app-home')
    attach_student_session_cookie(
        response,
        identity_id=result.identity.id,
        box_root_slug=result.identity.box_root_slug,
        device_fingerprint=build_student_device_fingerprint(view.request),
    )
    messages.success(view.request, 'Cadastro concluido. Seu app do aluno ja esta pronto para uso.')
    return response


def complete_student_imported_lead_onboarding(view, form):
    result = view._get_onboarding_workflow().complete_imported_lead_onboarding(
        pending_onboarding=view.pending_onboarding,
        cleaned_data=form.cleaned_data,
    )
    if not result.is_success:
        messages.error(view.request, result.error_message)
        clear_pending_student_onboarding(view.request)
        return redirect('student-app-home')
    clear_pending_student_onboarding(view.request)
    messages.success(view.request, 'Dados revisados. Agora voce pode usar o app normalmente.')
    return redirect('student-app-home')


def complete_student_onboarding(view, form):
    journey = view.pending_onboarding.get('journey')
    if journey == StudentOnboardingJourney.IMPORTED_LEAD_INVITE:
        return complete_student_imported_lead_onboarding(view, form)
    return complete_student_mass_onboarding(view, form)


__all__ = [
    'complete_student_imported_lead_onboarding',
    'complete_student_mass_onboarding',
    'complete_student_onboarding',
]
