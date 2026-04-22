"""
ARQUIVO: selecao de form e contexto do wizard de onboarding.

POR QUE ELE EXISTE:
- tira da view a montagem do wizard sem misturar apresentacao com conclusao do onboarding.

O QUE ESTE ARQUIVO FAZ:
1. escolhe o form pela jornada.
2. monta os kwargs iniciais do form.
3. monta o contexto textual do wizard.

PONTOS CRITICOS:
- manter as copies e o contrato do template estaveis.
- nao puxar mutacao para esta camada.
"""

from student_identity.models import StudentOnboardingJourney
from student_app.forms import ImportedLeadOnboardingForm, MassInviteOnboardingForm


def get_student_onboarding_form_class(*, pending_onboarding):
    journey = pending_onboarding.get('journey')
    if journey == StudentOnboardingJourney.IMPORTED_LEAD_INVITE:
        return ImportedLeadOnboardingForm
    return MassInviteOnboardingForm


def build_student_onboarding_form_kwargs(view):
    kwargs = super(type(view), view).get_form_kwargs()
    initial = kwargs.setdefault('initial', {})
    journey = view.pending_onboarding.get('journey')
    kwargs['box_root_slug'] = view.pending_onboarding.get('box_root_slug', '')
    kwargs['identity'] = view._get_pending_identity()
    kwargs['student'] = None
    initial.setdefault('email', view.pending_onboarding.get('email', ''))
    if journey == StudentOnboardingJourney.IMPORTED_LEAD_INVITE:
        student = view._get_existing_student()
        kwargs['student'] = student
        if student is not None:
            initial.setdefault('full_name', student.full_name)
            initial.setdefault('phone', student.phone)
            initial.setdefault('email', student.email or view.pending_onboarding.get('email', ''))
            initial.setdefault('birth_date', student.birth_date)
    return kwargs


def build_student_onboarding_context(view, **kwargs):
    context = super(type(view), view).get_context_data(**kwargs)
    journey = view.pending_onboarding.get('journey')
    context['journey'] = journey
    context['journey_title'] = (
        'Complete seu cadastro no app'
        if journey == StudentOnboardingJourney.MASS_BOX_INVITE
        else 'Revise seus dados para entrar no app'
    )
    context['journey_copy'] = (
        'Aqui a gente pega os dados essenciais para seu acesso nascer redondo.'
        if journey == StudentOnboardingJourney.MASS_BOX_INVITE
        else 'Ja puxamos o que o box sabia sobre voce. Agora falta so uma revisao curta.'
    )
    return context


__all__ = [
    'build_student_onboarding_context',
    'build_student_onboarding_form_kwargs',
    'get_student_onboarding_form_class',
]
