"""
ARQUIVO: gate de entrada — tela de consentimento (Onda B).

POR QUE ELE EXISTE:
- corredor unico de waiver + PAR-Q pos-auth para os 3 corredores de onboarding.

PONTOS CRITICOS:
- usa StudentAnyMembershipMixin (resolve identidade sem exigir membership ativo).
- o gate em StudentIdentityRequiredMixin.dispatch PULA esta rota (evita loop).
- a decisao clear/flagged e a gravacao moram no workflow, nao aqui.
"""
from __future__ import annotations

from django.shortcuts import redirect
from django.views.generic import FormView, TemplateView

from student_identity.funnel_events import record_student_onboarding_event
from student_identity.models import StudentConsentDocument, StudentConsentDocumentKind
from student_app.forms import StudentConsentForm
from student_app.workflows.consent_workflows import ENTRY_GATE_JOURNEY, record_consent
from .base import StudentAnyMembershipMixin


class StudentConsentView(StudentAnyMembershipMixin, FormView):
    template_name = 'student_app/consent.html'
    form_class = StudentConsentForm

    def get(self, request, *args, **kwargs):
        record_student_onboarding_event(
            journey=ENTRY_GATE_JOURNEY,
            event='consent_step_viewed',
            target_label=request.student_identity.student_name,
            description='Tela de consentimento exibida.',
            metadata={
                'box_root_slug': request.student_active_box_root_slug,
                'identity_id': request.student_identity.id,
            },
        )
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['waiver_document'] = StudentConsentDocument.objects.filter(
            kind=StudentConsentDocumentKind.WAIVER, is_active=True,
        ).first()
        context.setdefault('student_shell_nav', 'home')
        return self._attach_student_shell_context(context)

    def form_valid(self, form):
        request = self.request
        record_consent(
            identity=request.student_identity,
            box=getattr(request.student_identity, 'box', None),
            box_root_slug=request.student_active_box_root_slug,
            is_flagged=form.is_flagged,
            ip=request.META.get('REMOTE_ADDR', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
        return redirect('student-app-home')


class StudentClearanceView(StudentAnyMembershipMixin, TemplateView):
    """Parede de bloqueio do gate de entrada (Onda C).

    Mostrada quando o membership do box ativo esta clearance_required e ainda nao
    foi liberado. Nao e dead-end: instrui a levar o atestado ao box. A liberacao e
    manual (Onda D). O gate (b) em dispatch pula esta rota (evita loop).
    """

    template_name = 'student_app/clearance.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        membership = next(
            (
                m for m in self.request.student_box_memberships
                if m.box_root_slug == self.request.student_active_box_root_slug
            ),
            None,
        )
        context['clearance_membership'] = membership
        context['clearance_box'] = getattr(membership, 'box', None) if membership is not None else None
        context.setdefault('student_shell_nav', 'home')
        return self._attach_student_shell_context(context)
