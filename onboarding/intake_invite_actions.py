"""
ARQUIVO: actions de convite e handoff WhatsApp da Central de Intake.

POR QUE ELE EXISTE:
- separa da view a mutacao mais sensivel do intake: vincular aluno, criar convite e abrir o handoff no WhatsApp.

O QUE ESTE ARQUIVO FAZ:
1. valida limite operacional diario de convites para leads importados.
2. resolve ou cria o aluno vinculado ao intake.
3. cria convite do app para onboarding reduzido.
4. registra auditoria de handoff e evento do funil.

PONTOS CRITICOS:
- esse corredor mexe com aluno, convite, onboarding e WhatsApp ao mesmo tempo.
- qualquer mudanca aqui precisa preservar limite diario, redirects e auditoria do handoff.
"""

from django.conf import settings
from django.shortcuts import redirect
from django.utils import timezone

from django.contrib import messages

from onboarding.models import IntakeSource, IntakeStatus, StudentIntake
from shared_support.box_runtime import get_box_runtime_slug
from shared_support.crypto_fields import generate_blind_index
from student_identity.application.commands import CreateStudentInvitationCommand
from student_identity.application.use_cases import CreateStudentInvitation
from student_identity.delivery_audit import record_student_invitation_whatsapp_handoff
from student_identity.funnel_events import record_student_onboarding_event
from student_identity.infrastructure.repositories import DjangoStudentIdentityRepository
from student_identity.models import StudentAppInvitation, StudentOnboardingJourney
from student_identity.notifications import build_invitation_whatsapp_url
from students.models import Student, StudentStatus


def send_intake_whatsapp_invite(*, request, role_slug: str, get_success_url):
    return_query = request.POST.get('return_query', '')
    daily_limit = max(1, int(getattr(settings, 'STUDENT_IMPORTED_LEAD_WHATSAPP_DAILY_LIMIT', 25)))
    invites_today = StudentAppInvitation.objects.filter(
        created_by=request.user,
        onboarding_journey=StudentOnboardingJourney.IMPORTED_LEAD_INVITE,
        created_at__date=timezone.localdate(),
    ).count()
    if invites_today >= daily_limit:
        messages.error(request, f'O limite operacional de {daily_limit} convites por dia para leads importados foi alcancado.')
        return redirect(get_success_url(return_query))

    intake = StudentIntake.objects.select_for_update().select_related('linked_student').filter(
        pk=request.POST.get('intake_id')
    ).first()
    if intake is None:
        messages.error(request, 'Nao encontrei esse lead para disparar o convite por WhatsApp.')
        return redirect(get_success_url(return_query))
    if intake.source != IntakeSource.IMPORT:
        messages.error(request, 'O convite 1 clique por WhatsApp fica restrito a leads de Importacao externa.')
        return redirect(get_success_url(return_query))
    if not intake.phone:
        messages.error(request, 'Esse lead nao tem WhatsApp utilizavel para convite.')
        return redirect(get_success_url(return_query))

    student = intake.linked_student or resolve_or_create_student_from_intake(intake=intake)
    if intake.linked_student_id is None:
        intake.linked_student = student
        intake.status = IntakeStatus.MATCHED
        intake.save(update_fields=['linked_student', 'status', 'updated_at'])

    result = CreateStudentInvitation(DjangoStudentIdentityRepository()).execute(
        CreateStudentInvitationCommand(
            student_id=student.id,
            invited_email=(student.email or '').strip().lower(),
            box_root_slug=get_box_runtime_slug(),
            onboarding_journey=StudentOnboardingJourney.IMPORTED_LEAD_INVITE,
            actor_id=request.user.id,
        )
    )
    if not result.success or result.invitation is None:
        messages.error(request, 'Nao foi possivel preparar o convite do lead para o app agora.')
        return redirect(get_success_url(return_query))

    invitation = StudentAppInvitation.objects.select_related('student').get(pk=result.invitation.id)
    invite_url = request.build_absolute_uri(
        f"/aluno/auth/invite/{invitation.token}/"
    )
    whatsapp_url = build_invitation_whatsapp_url(invitation=invitation, invite_url=invite_url)
    if not whatsapp_url:
        messages.error(request, 'Nao foi possivel abrir o WhatsApp para esse lead agora.')
        return redirect(get_success_url(return_query))

    record_student_invitation_whatsapp_handoff(
        invitation=invitation,
        actor=request.user,
        recipient=student.phone,
        metadata={'invite_url': invite_url, 'source': 'intake_center'},
    )
    record_student_onboarding_event(
        actor=request.user,
        actor_role=role_slug,
        journey=StudentOnboardingJourney.IMPORTED_LEAD_INVITE,
        event='whatsapp_handoff_opened',
        target_model='student_identity.StudentAppInvitation',
        target_id=str(invitation.id),
        target_label=student.full_name,
        description='Handoff do WhatsApp aberto a partir da Central de Entradas.',
        metadata={
            'box_root_slug': get_box_runtime_slug(),
            'student_id': student.id,
            'invitation_id': invitation.id,
            'intake_id': intake.id,
            'source_surface': 'intake_center',
        },
    )
    return redirect(whatsapp_url)


def resolve_or_create_student_from_intake(*, intake: StudentIntake):
    phone_lookup_index = generate_blind_index(intake.phone)
    student = None
    if phone_lookup_index:
        student = Student.objects.filter(phone_lookup_index=phone_lookup_index).first()
    if student is not None:
        return student
    return Student.objects.create(
        full_name=intake.full_name,
        phone=intake.phone,
        email=getattr(intake, 'email', '') or '',
        status=StudentStatus.LEAD,
    )


__all__ = ['resolve_or_create_student_from_intake', 'send_intake_whatsapp_invite']
