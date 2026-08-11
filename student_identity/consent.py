"""
ARQUIVO: leitura do estado de consentimento do gate de entrada (Onda B).

POR QUE ELE EXISTE:
- o gate em StudentIdentityRequiredMixin.dispatch() (student_app/views/base.py)
  e a StudentConsentView precisam da MESMA definicao de "consentimento em dia".
  Centralizar aqui evita que dispatch() e a view divirjam sobre o que conta
  como aceito, o que abriria uma brecha (ou um loop de redirect).

O QUE ESTE ARQUIVO FAZ:
1. resolve os documentos de consentimento ATIVOS por kind.
2. decide se uma identidade tem consentimento em dia para um box.

PONTOS CRITICOS:
- fail-open se nao houver nenhum documento ATIVO (ex.: seed_consent_documents
  nao rodou neste ambiente): melhor deixar o aluno entrar do que travar o app
  inteiro por uma falha operacional de seed. Ver decisao registrada em
  docs/plans/student-parq-waiver-entry-gate-corda.md (secao 6.1).
"""

from __future__ import annotations

from .models import StudentConsent, StudentConsentDocument, StudentOnboardingJourney


def resolve_onboarding_journey_for_membership(membership) -> str:
    """Journey para instrumentar eventos ligados a um membership (consent, clearance).

    `membership.created_from_invite` costuma ser None mesmo para
    mass_box_invite/imported_lead_invite (o OnboardingWorkflow salva a
    identidade com invitation=None). Default: REGISTERED_STUDENT_INVITE quando
    nao ha invite associado — ver docs/plans/student-parq-waiver-entry-gate-corda.md,
    Onda B, "decisoes tomadas na implementacao".
    """
    invitation = membership.created_from_invite if membership is not None else None
    if invitation is not None:
        return invitation.onboarding_journey
    return StudentOnboardingJourney.REGISTERED_STUDENT_INVITE


def get_active_consent_documents() -> dict[str, StudentConsentDocument]:
    return {document.kind: document for document in StudentConsentDocument.objects.filter(is_active=True)}


def has_current_consent(*, identity, box_root_slug: str) -> bool:
    active_documents = get_active_consent_documents()
    if not active_documents:
        return True
    accepted_versions = set(
        StudentConsent.objects.filter(identity=identity, box_root_slug=box_root_slug).values_list(
            'document_kind', 'version'
        )
    )
    return all(
        (kind, document.version) in accepted_versions for kind, document in active_documents.items()
    )
