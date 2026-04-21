"""
ARQUIVO: corredor de onboarding do aluno.

POR QUE ELE EXISTE:
- separa a entrada inicial do aluno das telas recorrentes do app.

O QUE ESTE ARQUIVO FAZ:
1. decide qual wizard usar por jornada.
2. conclui onboarding em massa ou por lead importado.
3. amarra auditoria, enrollment pendente e sessao inicial do aluno.
"""

from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import FormView

from student_identity.models import StudentOnboardingJourney
from student_app.workflows import OnboardingWorkflow
from .onboarding_actions import complete_student_onboarding
from .onboarding_context import (
    build_student_onboarding_context,
    build_student_onboarding_form_kwargs,
    get_student_onboarding_form_class,
)
from .onboarding_loader import ensure_student_onboarding_wizard_started, load_pending_student_onboarding


class StudentOnboardingWizardView(FormView):
    template_name = 'student_app/onboarding_wizard.html'
    onboarding_workflow_class = OnboardingWorkflow

    def dispatch(self, request, *args, **kwargs):
        self.pending_onboarding = load_pending_student_onboarding(request)
        if self.pending_onboarding is None:
            messages.warning(request, 'Sua sessao expirou durante o cadastro. Tente novamente.')
            return redirect('student-identity-login')
        self.pending_onboarding = ensure_student_onboarding_wizard_started(
            request=request,
            pending_onboarding=self.pending_onboarding,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        return get_student_onboarding_form_class(pending_onboarding=self.pending_onboarding)

    def get_form_kwargs(self):
        return build_student_onboarding_form_kwargs(self)

    def get_context_data(self, **kwargs):
        return build_student_onboarding_context(self, **kwargs)

    def form_valid(self, form):
        return complete_student_onboarding(self, form)

    def _get_onboarding_workflow(self):
        return self.onboarding_workflow_class()

    def _get_existing_student(self):
        return self._get_onboarding_workflow().get_existing_student(pending_onboarding=self.pending_onboarding)

    def _get_pending_identity(self):
        return self._get_onboarding_workflow().get_pending_identity(pending_onboarding=self.pending_onboarding)
