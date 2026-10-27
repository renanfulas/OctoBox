"""
Seed de cenários de onboarding do aluno para QA.

Cria fixtures reutilizáveis cobrindo os 4 journeys principais:
- REGISTERED_STUDENT_INVITE (convite individual, aluno já cadastrado)
- IMPORTED_LEAD_INVITE (convite individual, lead importado)
- MASS_BOX_INVITE (link em massa)
- OPEN_BOX_INVITE (link aberto, aprovação manual)

Uso:
    python manage.py seed_onboarding_scenarios
    python manage.py seed_onboarding_scenarios --box-slug meu-box
    python manage.py seed_onboarding_scenarios --flush
"""
from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django_tenants.utils import schema_context
from django.utils import timezone

from control.models import Box
from control.tenant_write_fence import TenantFenceTargetMissing, TenantWritesFrozen, tenant_write_guard
from students.models import Student
from student_identity.models import (
    StudentAppInvitation,
    StudentBoxInviteLink,
    StudentInvitationType,
    StudentOnboardingJourney,
)

_DEFAULT_BOX = 'qa-box'


class Command(BaseCommand):
    help = 'Cria cenários de onboarding do aluno para QA.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--box-slug',
            default=_DEFAULT_BOX,
            help=f'Box root slug alvo (default: {_DEFAULT_BOX})',
        )
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Remove convites QA anteriores; preserva links sem marcador de propriedade.',
        )

    def handle(self, *args, **options):
        box_slug = options['box_slug'].strip()
        box = Box.objects.filter(slug=box_slug, status=Box.Status.ACTIVE).first()
        if box is None:
            raise CommandError(f'Box ativo não encontrado para slug {box_slug!r}.')

        try:
            with tenant_write_guard(box.schema_name):
                with schema_context(box.schema_name), transaction.atomic():
                    if options['flush']:
                        self._flush(box)
                    self._seed_registered_student_invite(box)
                    self._seed_imported_lead_invite(box)
                    self._seed_mass_box_invite(box)
                    self._seed_open_box_invite(box)
        except TenantWritesFrozen as exc:
            raise CommandError(
                f'Box {box.schema_name} está congelado; o seed de onboarding foi recusado.'
            ) from exc
        except TenantFenceTargetMissing as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(
            f'Cenários de onboarding criados para box "{box.slug}" ({box.schema_name}). '
            f'Consulte as invitations e box_invite_links no admin.'
        ))

    def _flush(self, box: Box):
        deleted_invites, _ = StudentAppInvitation.objects.filter(
            is_qa_seed=True,
        ).filter(Q(box=box) | Q(box__isnull=True, box_root_slug=box.schema_name)).delete()
        # StudentBoxInviteLink has no seed ownership marker. Preserve links rather
        # than risk deleting an operator-created link for the same Box.
        self.stdout.write(f'Flush: {deleted_invites} convites QA removidos; links existentes preservados.')

    def _get_or_create_student(self, *, full_name: str, email: str, phone: str) -> Student:
        student, _ = Student.objects.get_or_create(
            email=email,
            defaults={'full_name': full_name, 'phone': phone},
        )
        return student

    def _seed_registered_student_invite(self, box: Box):
        student = self._get_or_create_student(
            full_name='QA Aluno Registrado',
            email='qa-registered@qa.seed',
            phone='5511900000001',
        )
        invitation, _ = StudentAppInvitation.objects.get_or_create(
            is_qa_seed=True,
            box_root_slug=box.schema_name,
            onboarding_journey=StudentOnboardingJourney.REGISTERED_STUDENT_INVITE,
            invite_type=StudentInvitationType.INDIVIDUAL,
            defaults={
                'is_qa_seed': True,
                'invited_email': student.email,
                'box': box,
                'student_id': student.pk,
                'student_name': student.full_name,
                'expires_at': timezone.now() + timedelta(days=7),
            },
        )
        self._bind_invitation(invitation, box, student)
        self.stdout.write(f'  [OK] REGISTERED_STUDENT_INVITE — {student.email}')

    def _seed_imported_lead_invite(self, box: Box):
        student = self._get_or_create_student(
            full_name='QA Lead Importado',
            email='qa-lead@qa.seed',
            phone='5511900000002',
        )
        invitation, _ = StudentAppInvitation.objects.get_or_create(
            is_qa_seed=True,
            box_root_slug=box.schema_name,
            onboarding_journey=StudentOnboardingJourney.IMPORTED_LEAD_INVITE,
            invite_type=StudentInvitationType.INDIVIDUAL,
            defaults={
                'is_qa_seed': True,
                'invited_email': student.email,
                'box': box,
                'student_id': student.pk,
                'student_name': student.full_name,
                'expires_at': timezone.now() + timedelta(days=7),
            },
        )
        self._bind_invitation(invitation, box, student)
        self.stdout.write(f'  [OK] IMPORTED_LEAD_INVITE — {student.email}')

    def _bind_invitation(self, invitation: StudentAppInvitation, box: Box, student: Student) -> None:
        if invitation.box_id and invitation.box_id != box.pk:
            raise CommandError('Convite QA existente aponta para outro Box; nenhuma associação foi alterada.')
        changed_fields = []
        if invitation.box_id is None:
            invitation.box = box
            changed_fields.append('box')
        if invitation.student_id != student.pk:
            invitation.student_id = student.pk
            changed_fields.append('student_id')
        if invitation.student_name != student.full_name:
            invitation.student_name = student.full_name
            changed_fields.append('student_name')
        if not invitation.is_qa_seed:
            invitation.is_qa_seed = True
            changed_fields.append('is_qa_seed')
        if changed_fields:
            invitation.save(update_fields=changed_fields)

    def _seed_mass_box_invite(self, box: Box):
        link, created = StudentBoxInviteLink.objects.get_or_create(
            box_root_slug=box.schema_name,
            defaults={
                'box': box,
                'expires_at': timezone.now() + timedelta(days=30),
                'max_uses': 200,
            },
        )
        if link.box_id and link.box_id != box.pk:
            raise CommandError('Link de convite existente aponta para outro Box; nenhuma associação foi alterada.')
        if link.box_id is None:
            link.box = box
            link.save(update_fields=['box'])
        status = 'criado' if created else 'já existia'
        self.stdout.write(f'  [OK] MASS_BOX_INVITE — token={link.token} ({status})')

    def _seed_open_box_invite(self, box: Box):
        student = self._get_or_create_student(
            full_name='QA Aluno Aguardando Aprovação',
            email='qa-open-box@qa.seed',
            phone='5511900000003',
        )
        invitation, created = StudentAppInvitation.objects.get_or_create(
            is_qa_seed=True,
            box_root_slug=box.schema_name,
            onboarding_journey=StudentOnboardingJourney.REGISTERED_STUDENT_INVITE,
            invite_type=StudentInvitationType.OPEN_BOX,
            defaults={
                'is_qa_seed': True,
                'invited_email': student.email,
                'box': box,
                'student_id': student.pk,
                'student_name': student.full_name,
                'expires_at': timezone.now() + timedelta(days=7),
            },
        )
        self._bind_invitation(invitation, box, student)
        status = 'criado' if created else 'já existia'
        self.stdout.write(f'  [OK] OPEN_BOX_INVITE — {invitation.invited_email} ({status})')
