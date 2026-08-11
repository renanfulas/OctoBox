"""
Seed dos documentos de consentimento do gate de entrada (Onda A).

Garante a versao ATIVA do termo (waiver) e da triagem (PAR-Q). Idempotente:
pode rodar quantas vezes quiser.

IMPORTANTE — textos provisorios:
- waiver v1 = PLACEHOLDER_NAO_VINCULANTE. O texto juridico real (vinculante) so
  entra na Onda E; ate la nenhum aceite de waiver e tratado como vinculante.
- parq v1   = 7 perguntas canonicas do PAR-Q, marcado PENDENTE_REVISAO_CLINICA.
  Os red-flags so vao a producao apos revisao humana (idealmente profissional de
  saude), na Onda B.

Uso:
    python manage.py seed_consent_documents
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from student_identity.models import StudentConsentDocument, StudentConsentDocumentKind
from student_identity.parq_questions import PARQ_V1_VERSION, build_parq_v1_body


WAIVER_V1_VERSION = '1'

WAIVER_V1_BODY = """[PLACEHOLDER_NAO_VINCULANTE]

Termo de responsabilidade provisorio. NAO usar como documento juridico.
O texto vinculante real entra na Onda E, validado pelo juridico.""".strip()


# Corpo montado a partir de student_identity.parq_questions — fonte unica com o
# formulario de consentimento da Onda B. Nao duplique as perguntas aqui.
PARQ_V1_BODY = build_parq_v1_body()


_SEEDS = [
    (StudentConsentDocumentKind.WAIVER, WAIVER_V1_VERSION, WAIVER_V1_BODY),
    (StudentConsentDocumentKind.PARQ, PARQ_V1_VERSION, PARQ_V1_BODY),
]


class Command(BaseCommand):
    help = 'Garante a versao ativa do waiver e do PAR-Q (idempotente).'

    @transaction.atomic
    def handle(self, *args, **options):
        for kind, version, body in _SEEDS:
            # Garante a unicidade da versao ativa: desativa as demais do mesmo kind
            # ANTES de ativar a v1 (respeita unique_active_consent_document_per_kind).
            StudentConsentDocument.objects.filter(kind=kind).exclude(version=version).update(is_active=False)
            _document, created = StudentConsentDocument.objects.update_or_create(
                kind=kind,
                version=version,
                defaults={'body': body, 'is_active': True},
            )
            action = 'criado' if created else 'atualizado'
            self.stdout.write(f'{kind} v{version} {action} (ativo).')
        self.stdout.write(self.style.SUCCESS('Documentos de consentimento garantidos.'))
