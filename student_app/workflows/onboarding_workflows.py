"""
ARQUIVO: workflows de onboarding do app do aluno.

POR QUE ELE EXISTE:
- concentra as escritas mais densas do onboarding sem misturar auditoria, identidade e enrollment dentro da view.

O QUE ESTE ARQUIVO FAZ:
1. resolve aluno e identidade pendentes do onboarding.
2. conclui onboarding em massa.
3. conclui onboarding de lead importado.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from student_identity.funnel_events import record_student_onboarding_event
from student_identity.infrastructure.repositories import DjangoStudentIdentityRepository
from student_identity.models import StudentIdentity, StudentOnboardingJourney
from finance.models import Enrollment, EnrollmentStatus
from students.models import Student, StudentStatus


def ensure_pending_enrollment(*, student, plan, source_note: str):
    if plan is None:
        return None
    enrollment = (
        Enrollment.objects.filter(
            student=student,
            plan=plan,
            status__in=[EnrollmentStatus.PENDING, EnrollmentStatus.ACTIVE],
        )
        .order_by('-created_at')
        .first()
    )
    if enrollment is not None:
        return enrollment
    return Enrollment.objects.create(
        student=student,
        plan=plan,
        status=EnrollmentStatus.PENDING,
        notes=source_note,
    )


@dataclass(frozen=True)
class OnboardingCompletionResult:
    student: Student | None
    identity: StudentIdentity | None
    status: str
    error_message: str = ''

    @property
    def is_success(self) -> bool:
        return self.status == 'ok'


class OnboardingWorkflow:
    def __init__(self, *, identity_repository=None):
        self.identity_repository = identity_repository or DjangoStudentIdentityRepository()

    def get_existing_student(self, *, pending_onboarding):
        student_id = pending_onboarding.get('student_id')
        if not student_id:
            identity = self.get_pending_identity(pending_onboarding=pending_onboarding)
            return identity.student if identity is not None else None
        return Student.objects.filter(pk=student_id).first()

    def get_pending_identity(self, *, pending_onboarding):
        identity_id = pending_onboarding.get('identity_id')
        if not identity_id:
            return None
        return self.identity_repository.find_identity_by_id(identity_id)

    def get_pending_email(self, *, pending_onboarding) -> str:
        pending_email = (pending_onboarding.get('email') or '').strip().lower()
        if pending_email:
            return pending_email
        identity = self.get_pending_identity(pending_onboarding=pending_onboarding)
        return (getattr(identity, 'email', '') or '').strip().lower()

    @transaction.atomic
    def complete_mass_onboarding(self, *, pending_onboarding, cleaned_data) -> OnboardingCompletionResult:
        email = self.get_pending_email(pending_onboarding=pending_onboarding)
        student = Student.objects.create(
            full_name=cleaned_data['full_name'],
            phone=cleaned_data['phone'],
            email=email,
            birth_date=cleaned_data.get('birth_date'),
            status=StudentStatus.ACTIVE,
        )
        identity = self.identity_repository.save_identity(
            student=student,
            box_root_slug=pending_onboarding['box_root_slug'],
            provider=pending_onboarding['provider'],
            provider_subject=pending_onboarding['provider_subject'],
            email=email,
            invitation=None,
        )
        ensure_pending_enrollment(
            student=student,
            plan=cleaned_data.get('selected_plan'),
            source_note='Capturado via link em massa do onboarding do aluno.',
        )
        record_student_onboarding_event(
            actor=None,
            actor_role='',
            journey=StudentOnboardingJourney.MASS_BOX_INVITE,
            event='wizard_completed',
            target_model='student_identity.StudentIdentity',
            target_id=str(identity.id),
            target_label=student.full_name,
            description='Wizard completo do link em massa concluido.',
            metadata={
                'box_root_slug': identity.box_root_slug,
                'student_id': student.id,
                'identity_id': identity.id,
                'box_invite_link_id': pending_onboarding.get('box_invite_link_id'),
            },
        )
        record_student_onboarding_event(
            actor=None,
            actor_role='',
            journey=StudentOnboardingJourney.MASS_BOX_INVITE,
            event='app_entry_completed',
            target_model='student_identity.StudentIdentity',
            target_id=str(identity.id),
            target_label=student.full_name,
            description='Entrada no app concluida apos onboarding em massa.',
            metadata={
                'box_root_slug': identity.box_root_slug,
                'student_id': student.id,
                'identity_id': identity.id,
                'box_invite_link_id': pending_onboarding.get('box_invite_link_id'),
            },
        )
        return OnboardingCompletionResult(student=student, identity=identity, status='ok')

    @transaction.atomic
    def complete_imported_lead_onboarding(self, *, pending_onboarding, cleaned_data) -> OnboardingCompletionResult:
        identity = self.get_pending_identity(pending_onboarding=pending_onboarding)
        if identity is None:
            return OnboardingCompletionResult(
                student=None,
                identity=None,
                status='missing_identity',
                error_message='Nao conseguimos localizar a identidade ligada a este onboarding.',
            )

        student = self.get_existing_student(pending_onboarding=pending_onboarding)
        if student is None:
            return OnboardingCompletionResult(
                student=None,
                identity=identity,
                status='missing_student',
                error_message='Nao conseguimos localizar o aluno vinculado a este convite.',
            )

        student.full_name = cleaned_data['full_name']
        student.phone = cleaned_data['phone']
        student.email = self.get_pending_email(pending_onboarding=pending_onboarding)
        student.birth_date = cleaned_data.get('birth_date')
        if student.status == StudentStatus.LEAD:
            student.status = StudentStatus.ACTIVE
        student.save()
        if identity.email != student.email and student.email:
            identity.email = student.email
            identity.save(update_fields=['email', 'updated_at'])
        ensure_pending_enrollment(
            student=student,
            plan=cleaned_data.get('selected_plan'),
            source_note='Capturado via convite individual de lead importado.',
        )
        record_student_onboarding_event(
            actor=None,
            actor_role='',
            journey=StudentOnboardingJourney.IMPORTED_LEAD_INVITE,
            event='wizard_completed',
            target_model='student_identity.StudentIdentity',
            target_id=str(identity.id),
            target_label=student.full_name,
            description='Wizard reduzido do lead importado concluido.',
            metadata={
                'box_root_slug': identity.box_root_slug,
                'student_id': student.id,
                'identity_id': identity.id,
                'invitation_id': pending_onboarding.get('invitation_id'),
            },
        )
        record_student_onboarding_event(
            actor=None,
            actor_role='',
            journey=StudentOnboardingJourney.IMPORTED_LEAD_INVITE,
            event='app_entry_completed',
            target_model='student_identity.StudentIdentity',
            target_id=str(identity.id),
            target_label=student.full_name,
            description='Entrada no app concluida apos convite de lead importado.',
            metadata={
                'box_root_slug': identity.box_root_slug,
                'student_id': student.id,
                'identity_id': identity.id,
                'invitation_id': pending_onboarding.get('invitation_id'),
            },
        )
        return OnboardingCompletionResult(student=student, identity=identity, status='ok')
