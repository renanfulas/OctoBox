"""
ARQUIVO: gate de entrada — consentimento (waiver + PAR-Q), Onda B.

POR QUE ELE EXISTE:
- concentra a DECISAO do gate (clear/flagged), a leitura da versao vigente e a
  gravacao de StudentConsent fora de view/template (guardrail do plano).

PONTOS CRITICOS:
- o waiver e gravado como aceite NAO-vinculante (placeholder) ate a Onda E; por
  isso o evento `waiver_accepted` NAO e emitido aqui.
- guarda apenas o RESULTADO do PAR-Q (clear/flagged) — nunca as respostas.
- flagged marca clearance_required no membership (gate de saida vem na Onda C).
"""
from __future__ import annotations

from dataclasses import dataclass

from student_identity.funnel_events import record_student_onboarding_event
from student_identity.models import (
    StudentBoxMembership,
    StudentConsent,
    StudentConsentDocument,
    StudentConsentDocumentKind,
    StudentParqOutcome,
)

ENTRY_GATE_JOURNEY = 'entry_gate'


def active_consent_versions() -> dict[str, str]:
    """Versoes ativas de waiver e PAR-Q. Vazio se nao houver seed."""
    versions: dict[str, str] = {}
    for kind in (StudentConsentDocumentKind.WAIVER, StudentConsentDocumentKind.PARQ):
        document = StudentConsentDocument.objects.filter(kind=kind, is_active=True).first()
        if document is not None:
            versions[kind] = document.version
    return versions


def consent_is_pending(*, identity, box_root_slug: str) -> bool:
    """True se falta aceite da versao vigente de qualquer documento ativo."""
    versions = active_consent_versions()
    if not versions:
        return False  # sem documentos ativos => gate nao se aplica
    for kind, version in versions.items():
        already = StudentConsent.objects.filter(
            identity=identity,
            box_root_slug=box_root_slug,
            document_kind=kind,
            version=version,
        ).exists()
        if not already:
            return True
    return False


@dataclass
class ConsentResult:
    outcome: str
    clearance_required: bool


def record_consent(*, identity, box, box_root_slug, is_flagged, ip='', user_agent=''):
    """Grava o aceite das versoes vigentes, decide clear/flagged e (se flagged)
    marca clearance_required no membership do box ativo. Idempotente por versao."""
    versions = active_consent_versions()
    outcome = StudentParqOutcome.FLAGGED if is_flagged else StudentParqOutcome.CLEAR
    for kind, version in versions.items():
        StudentConsent.objects.update_or_create(
            identity=identity,
            box_root_slug=box_root_slug,
            document_kind=kind,
            version=version,
            defaults={
                'box': box,
                'ip': ip or None,
                'user_agent': (user_agent or '')[:400],
                'parq_outcome': outcome if kind == StudentConsentDocumentKind.PARQ else '',
            },
        )

    record_student_onboarding_event(
        journey=ENTRY_GATE_JOURNEY,
        event='parq_completed',
        target_model='student_identity.StudentConsent',
        target_id=str(identity.id),
        target_label=identity.student_name,
        description='PAR-Q concluido no gate de entrada.',
        metadata={'box_root_slug': box_root_slug, 'identity_id': identity.id, 'outcome': str(outcome)},
    )

    clearance_required = False
    if is_flagged:
        clearance_required = True
        record_student_onboarding_event(
            journey=ENTRY_GATE_JOURNEY,
            event='parq_flagged',
            target_model='student_identity.StudentConsent',
            target_id=str(identity.id),
            target_label=identity.student_name,
            description='PAR-Q sinalizou risco no gate de entrada.',
            metadata={'box_root_slug': box_root_slug, 'identity_id': identity.id},
        )
        membership = StudentBoxMembership.objects.filter(
            identity=identity, box_root_slug=box_root_slug,
        ).first()
        if membership is not None and not membership.clearance_required:
            membership.clearance_required = True
            membership.save(update_fields=['clearance_required', 'updated_at'])
            record_student_onboarding_event(
                journey=ENTRY_GATE_JOURNEY,
                event='clearance_pending',
                target_model='student_identity.StudentBoxMembership',
                target_id=str(membership.id),
                target_label=identity.student_name,
                description='Membership aguardando liberacao por atestado.',
                metadata={'box_root_slug': box_root_slug, 'identity_id': identity.id},
            )

    return ConsentResult(outcome=str(outcome), clearance_required=clearance_required)
