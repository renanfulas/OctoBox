"""
Onda A do gate de entrada — fundacao de dados.

Cobre o que sustenta o verde da homologacao desta onda:
- seed idempotente com uma unica versao ativa por kind
- constraint de versao ativa unica por kind
- constraint de aceite unico por (identity, box, kind, version)
- mark_cleared set-once no membership
"""
from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase

from student_identity.models import (
    StudentConsent,
    StudentConsentDocument,
    StudentConsentDocumentKind,
    StudentIdentity,
    StudentIdentityProvider,
    StudentParqOutcome,
    StudentBoxMembership,
)


def _seed():
    call_command('seed_consent_documents', stdout=StringIO())


def _make_identity(subject='subject-1'):
    return StudentIdentity.objects.create(
        provider=StudentIdentityProvider.GOOGLE,
        provider_subject=subject,
        email=f'{subject}@example.com',
        student_name='Aluno Teste',
        box_root_slug='demo-box',
    )


class SeedConsentDocumentsTests(TestCase):
    def test_seed_creates_single_active_per_kind(self):
        _seed()
        for kind in (StudentConsentDocumentKind.WAIVER, StudentConsentDocumentKind.PARQ):
            active = StudentConsentDocument.objects.filter(kind=kind, is_active=True)
            self.assertEqual(active.count(), 1, kind)
            self.assertEqual(active.first().version, '1')

    def test_seed_is_idempotent(self):
        _seed()
        _seed()
        self.assertEqual(StudentConsentDocument.objects.count(), 2)
        self.assertEqual(
            StudentConsentDocument.objects.filter(is_active=True).count(), 2
        )

    def test_parq_seed_is_marked_pending_clinical_review(self):
        _seed()
        parq = StudentConsentDocument.objects.get(kind=StudentConsentDocumentKind.PARQ, version='1')
        self.assertIn('PENDENTE_REVISAO_CLINICA', parq.body)

    def test_waiver_seed_is_marked_non_binding_placeholder(self):
        _seed()
        waiver = StudentConsentDocument.objects.get(kind=StudentConsentDocumentKind.WAIVER, version='1')
        self.assertIn('PLACEHOLDER_NAO_VINCULANTE', waiver.body)


class ConsentDocumentConstraintTests(TestCase):
    def test_only_one_active_version_per_kind(self):
        StudentConsentDocument.objects.create(
            kind=StudentConsentDocumentKind.WAIVER, version='1', is_active=True
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                StudentConsentDocument.objects.create(
                    kind=StudentConsentDocumentKind.WAIVER, version='2', is_active=True
                )

    def test_inactive_versions_can_coexist(self):
        StudentConsentDocument.objects.create(
            kind=StudentConsentDocumentKind.WAIVER, version='1', is_active=True
        )
        StudentConsentDocument.objects.create(
            kind=StudentConsentDocumentKind.WAIVER, version='2', is_active=False
        )
        self.assertEqual(StudentConsentDocument.objects.filter(kind=StudentConsentDocumentKind.WAIVER).count(), 2)


class StudentConsentConstraintTests(TestCase):
    def test_unique_consent_per_identity_box_kind_version(self):
        identity = _make_identity()
        StudentConsent.objects.create(
            identity=identity,
            box_root_slug='demo-box',
            document_kind=StudentConsentDocumentKind.PARQ,
            version='1',
            parq_outcome=StudentParqOutcome.CLEAR,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                StudentConsent.objects.create(
                    identity=identity,
                    box_root_slug='demo-box',
                    document_kind=StudentConsentDocumentKind.PARQ,
                    version='1',
                    parq_outcome=StudentParqOutcome.FLAGGED,
                )


class MarkClearedTests(TestCase):
    def test_mark_cleared_is_set_once(self):
        identity = _make_identity('subject-clear')
        membership = StudentBoxMembership(
            identity=identity,
            box_root_slug='demo-box',
            clearance_required=True,
        )
        membership.mark_cleared(by=None)
        first = membership.cleared_at
        self.assertIsNotNone(first)
        # segunda chamada nao move o timestamp (idempotente)
        membership.mark_cleared(by=None)
        self.assertEqual(membership.cleared_at, first)
        # fato historico preservado
        self.assertTrue(membership.clearance_required)
