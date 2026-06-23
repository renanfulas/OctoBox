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


WAIVER_V1_BODY = """[PLACEHOLDER_NAO_VINCULANTE]

Termo de responsabilidade provisorio. NAO usar como documento juridico.
O texto vinculante real entra na Onda E, validado pelo juridico.""".strip()


PARQ_V1_BODY = """[PENDENTE_REVISAO_CLINICA]

Questionario de Prontidao para Atividade Fisica (PAR-Q). 7 perguntas canonicas.
Responder "sim" a qualquer uma sinaliza risco e exige liberacao por atestado no box.

1. Algum medico ja disse que voce possui algum problema de coracao e que so deveria
   realizar atividade fisica supervisionada por profissionais de saude?
2. Voce sente dores no peito quando pratica atividade fisica?
3. No ultimo mes, voce sentiu dores no peito quando praticou atividade fisica?
4. Voce apresenta desequilibrio devido a tontura e/ou perda de consciencia?
5. Voce possui algum problema osseo ou articular que poderia ser piorado pela
   mudanca na sua atividade fisica?
6. Voce toma atualmente algum medicamento para pressao arterial e/ou problema de coracao?
7. Sabe de alguma outra razao pela qual voce nao deveria praticar atividade fisica?""".strip()


_SEEDS = [
    (StudentConsentDocumentKind.WAIVER, '1', WAIVER_V1_BODY),
    (StudentConsentDocumentKind.PARQ, '1', PARQ_V1_BODY),
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
