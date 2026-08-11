"""
ARQUIVO: gate de consentimento (PAR-Q + termo) do app do aluno — Onda B.

POR QUE ELE EXISTE:
- implementa as duas telas do gate de entrada descrito em
  docs/plans/student-parq-waiver-entry-gate-corda.md: consentimento
  (PAR-Q + termo) e a parede de liberacao pendente (clearance).
- decide clear/flagged aqui, nunca em template/view generica (guardrail do plano).

O QUE ESTE ARQUIVO FAZ:
1. StudentConsentView: mostra o PAR-Q (toggles Sim/Nao) + termo (so leitura,
   nao vinculante nesta onda); grava StudentConsent e decide clear/flagged.
2. StudentClearanceView: parede acolhedora para quem ficou com clearance_required.

PONTOS CRITICOS:
- a versao gravada e a LIDA na tela (hidden fields), nunca a vigente no submit.
- `parq_version`/`waiver_version` submetidos sao validados contra documentos
  REAIS antes de aceitar qualquer resposta — um `parq_version` forjado sem
  perguntas conhecidas nunca produz outcome "clear" por omissao.
- dado de saude detalhado (quais respostas) nunca e persistido; so o outcome.
"""

from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.generic import View

from student_app.forms import StudentConsentForm
from student_identity.consent import (
    get_active_consent_documents,
    has_current_consent,
    resolve_onboarding_journey_for_membership,
)
from student_identity.funnel_events import record_student_onboarding_event
from student_identity.models import (
    StudentConsent,
    StudentConsentDocument,
    StudentConsentDocumentKind,
    StudentParqOutcome,
)
from student_identity.parq_questions import PARQ_QUESTIONS_BY_VERSION
from student_identity.security import resolve_student_client_ip

from .base import StudentIdentityRequiredMixin


class StudentConsentView(StudentIdentityRequiredMixin, View):
    template_name = 'student_app/consent.html'

    def _render(self, request, form, waiver_body):
        context = self._attach_student_shell_context({
            'form': form,
            'waiver_body': waiver_body,
        })
        return render(request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        membership = getattr(request, 'student_active_membership', None)
        if membership is not None and membership.clearance_required and not membership.cleared_at:
            return redirect('student-app-clearance')
        if membership is not None and has_current_consent(
            identity=request.student_identity, box_root_slug=membership.box_root_slug
        ):
            return redirect('student-app-home')

        active_documents = get_active_consent_documents()
        parq_document = active_documents.get(StudentConsentDocumentKind.PARQ)
        waiver_document = active_documents.get(StudentConsentDocumentKind.WAIVER)
        questions = PARQ_QUESTIONS_BY_VERSION.get(parq_document.version, ()) if parq_document else ()
        if parq_document is None or waiver_document is None or not questions:
            messages.error(
                request,
                'Nao foi possivel carregar o formulario de consentimento agora. Tente novamente em instantes.',
            )
            return redirect('student-app-home')

        form = StudentConsentForm(
            questions=questions,
            initial={'parq_version': parq_document.version, 'waiver_version': waiver_document.version},
        )
        return self._render(request, form, waiver_document.body)

    def post(self, request, *args, **kwargs):
        submitted_parq_version = (request.POST.get('parq_version') or '').strip()
        submitted_waiver_version = (request.POST.get('waiver_version') or '').strip()
        questions = PARQ_QUESTIONS_BY_VERSION.get(submitted_parq_version, ())
        parq_document = (
            StudentConsentDocument.objects.filter(
                kind=StudentConsentDocumentKind.PARQ, version=submitted_parq_version
            ).first()
            if submitted_parq_version
            else None
        )
        waiver_document = (
            StudentConsentDocument.objects.filter(
                kind=StudentConsentDocumentKind.WAIVER, version=submitted_waiver_version
            ).first()
            if submitted_waiver_version
            else None
        )
        # versao forjada/desconhecida: nao ha perguntas para validar contra ela,
        # entao recarrega o formulario do zero em vez de aceitar respostas vazias.
        if not questions or parq_document is None or waiver_document is None:
            messages.error(request, 'Sua sessao do formulario expirou. Preencha novamente.')
            return redirect('student-app-consent')

        form = StudentConsentForm(request.POST, questions=questions)
        if not form.is_valid():
            return self._render(request, form, waiver_document.body)

        identity = request.student_identity
        membership = getattr(request, 'student_active_membership', None)
        box_root_slug = membership.box_root_slug if membership is not None else request.student_active_box_root_slug
        journey = resolve_onboarding_journey_for_membership(membership)
        outcome = form.compute_parq_outcome()
        ip = resolve_student_client_ip(request)
        user_agent = (request.META.get('HTTP_USER_AGENT') or '')[:400]
        now = timezone.now()

        record_student_onboarding_event(
            journey=journey,
            event='consent_step_viewed',
            target_model='student_identity.StudentIdentity',
            target_id=str(identity.id),
            target_label=identity.student_name,
            description='Aluno enviou o formulario de consentimento do gate de entrada.',
            metadata={'box_root_slug': box_root_slug},
        )

        # Onda B: aceite do waiver e gravado (satisfaz o gate), mas NAO e tratado
        # como vinculante — o texto ainda e o placeholder. Por isso nao disparamos
        # o evento `waiver_accepted` aqui; ele so liga na Onda E com texto real.
        StudentConsent.objects.update_or_create(
            identity=identity,
            box_root_slug=box_root_slug,
            document_kind=StudentConsentDocumentKind.WAIVER,
            version=waiver_document.version,
            defaults={'accepted_at': now, 'ip': ip, 'user_agent': user_agent},
        )
        StudentConsent.objects.update_or_create(
            identity=identity,
            box_root_slug=box_root_slug,
            document_kind=StudentConsentDocumentKind.PARQ,
            version=parq_document.version,
            defaults={'accepted_at': now, 'ip': ip, 'user_agent': user_agent, 'parq_outcome': outcome},
        )
        record_student_onboarding_event(
            journey=journey,
            event='parq_completed',
            target_model='student_identity.StudentIdentity',
            target_id=str(identity.id),
            target_label=identity.student_name,
            description='PAR-Q concluido no gate de entrada.',
            metadata={'box_root_slug': box_root_slug, 'outcome': outcome},
        )

        if outcome == StudentParqOutcome.FLAGGED:
            if membership is not None and not membership.clearance_required:
                membership.clearance_required = True
                membership.save(update_fields=['clearance_required', 'updated_at'])
            record_student_onboarding_event(
                journey=journey,
                event='parq_flagged',
                target_model='student_identity.StudentBoxMembership',
                target_id=str(membership.id) if membership is not None else '',
                target_label=identity.student_name,
                description='PAR-Q sinalizou risco; entrada bloqueada ate liberacao manual.',
                metadata={'box_root_slug': box_root_slug},
            )
            record_student_onboarding_event(
                journey=journey,
                event='clearance_pending',
                target_model='student_identity.StudentBoxMembership',
                target_id=str(membership.id) if membership is not None else '',
                target_label=identity.student_name,
                description='Aluno aguardando liberacao manual por atestado no box.',
                metadata={'box_root_slug': box_root_slug},
            )
            return redirect('student-app-clearance')

        messages.success(request, 'Consentimento registrado. Bem-vindo(a)!')
        return redirect('student-app-home')


class StudentClearanceView(StudentIdentityRequiredMixin, View):
    template_name = 'student_app/clearance.html'

    def get(self, request, *args, **kwargs):
        membership = getattr(request, 'student_active_membership', None)
        if membership is None or not membership.clearance_required or membership.cleared_at is not None:
            return redirect('student-app-home')
        context = self._attach_student_shell_context({'clearance_membership': membership})
        return render(request, self.template_name, context)
