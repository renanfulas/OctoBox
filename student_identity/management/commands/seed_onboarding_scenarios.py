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

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from students.models import Student
from student_identity.models import (
    StudentAppInvitation,
    StudentBoxInviteLink,
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
            help='Remove dados de seed anteriores antes de criar novos.',
        )

    def handle(self, *args, **options):
        box_slug = options['box_slug']
        if options['flush']:
            self._flush(box_slug)

        with transaction.atomic():
            self._seed_registered_student_invite(box_slug)
            self._seed_imported_lead_invite(box_slug)
            self._seed_mass_box_invite(box_slug)
            self._seed_open_box_invite(box_slug)

        self.stdout.write(self.style.SUCCESS(
            f'Cenários de onboarding criados para box "{box_slug}". '
            f'Consulte as invitations e box_invite_links no admin.'
        ))

    def _flush(self, box_slug: str):
        deleted_invites, _ = StudentAppInvitation.objects.filter(
            box_root_slug=box_slug,
            invited_email__endswith='@qa.seed',
        ).delete()
        deleted_links, _ = StudentBoxInviteLink.objects.filter(
            box_root_slug=box_slug,
        ).delete()
        self.stdout.write(f'Flush: {deleted_invites} convites e {deleted_links} links removidos.')

    def _get_or_create_student(self, *, full_name: str, email: str, phone: str) -> Student:
        student, _ = Student.objects.get_or_create(
            email=email,
            defaults={'full_name': full_name, 'phone': phone},
        )
        return student

    def _seed_registered_student_invite(self, box_slug: str):
        student = self._get_or_create_student(
            full_name='QA Aluno Registrado',
            email='qa-registered@qa.seed',
            phone='5511900000001',
        )
        StudentAppInvitation.objects.get_or_create(
            invited_email=student.email,
            box_root_slug=box_slug,
            onboarding_journey=StudentOnboardingJourney.REGISTERED_STUDENT_INVITE,
            defaults={
                'student': student,
                'expires_at': timezone.now() + timedelta(days=7),
            },
        )
        self.stdout.write(f'  [OK] REGISTERED_STUDENT_INVITE — {student.email}')

    def _seed_imported_lead_invite(self, box_slug: str):
        student = self._get_or_create_student(
            full_name='QA Lead Importado',
            email='qa-lead@qa.seed',
            phone='5511900000002',
        )
        StudentAppInvitation.objects.get_or_create(
            invited_email=student.email,
            box_root_slug=box_slug,
            onboarding_journey=StudentOnboardingJourney.IMPORTED_LEAD_INVITE,
            defaults={
                'student': student,
                'expires_at': timezone.now() + timedelta(days=7),
            },
        )
        self.stdout.write(f'  [OK] IMPORTED_LEAD_INVITE — {student.email}')

    def _seed_mass_box_invite(self, box_slug: str):
        link, created = StudentBoxInviteLink.objects.get_or_create(
            box_root_slug=box_slug,
            defaults={'expires_at': timezone.now() + timedelta(days=30), 'max_uses': 200},
        )
        status = 'criado' if created else 'já existia'
        self.stdout.write(f'  [OK] MASS_BOX_INVITE — token={link.token} ({status})')
