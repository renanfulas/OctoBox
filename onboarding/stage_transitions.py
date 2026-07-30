"""
ARQUIVO: ponto unico de transicao de estagio do intake.

POR QUE ELE EXISTE:
- as transicoes de StudentIntake.status estavam espalhadas por 3 arquivos
  (onboarding/facade.py, onboarding/intake_invite_actions.py,
  students/infrastructure/django_intakes.py), todas gravando so `status`,
  sem datar desfecho e sem deixar trilha auditavel consistente.
- sem desfecho datado nao existe janela de maturacao, e sem ela toda taxa
  de conversao subestima o resultado real (censura a direita). Ver
  auditoria de leads 2026-07-28, achados M18 e A3.

O QUE ESTE ARQUIVO FAZ:
1. muda o status do StudentIntake.
2. data o desfecho terminal (converted_at/rejected_at) na primeira vez que
   o status chega la — nunca sobrescreve um valor ja gravado.
3. emite audit event padronizado (`intake_stage_changed`) com o motivo.

PONTOS CRITICOS:
- este e o UNICO caminho legitimo de mutacao de StudentIntake.status. Nenhum
  outro lugar do codebase deve chamar intake.save(update_fields=[...,'status',...])
  diretamente — isso deixaria de datar desfecho e de deixar rastro.
- MATCHED (convite disparado) NAO e conversao comercial — so a transicao
  para APPROVED grava converted_at e conversion_kind. O convite preenche
  linked_student por motivo de identidade, nao de conversao (ver achado A3
  e a decisao registrada em docs/plans/leads-ml-foundation-and-network-intelligence-plan.md).
"""

from __future__ import annotations

from datetime import datetime

from django.utils import timezone

from auditing import log_audit_event
from onboarding.models import IntakeStatus

TERMINAL_TIMESTAMP_FIELD = {
    IntakeStatus.APPROVED: 'converted_at',
    IntakeStatus.REJECTED: 'rejected_at',
}


def transition_intake_status(
    *,
    intake,
    to_status: str,
    actor=None,
    surface: str = '',
    conversion_kind: str = '',
    now: datetime | None = None,
    extra_update_fields: tuple = (),
):
    """Muda o status do intake, data o desfecho terminal e emite audit event.

    `extra_update_fields` permite ao chamador incluir campos que ele mesmo
    ja alterou na mesma instancia (ex: linked_student, phone) para irem no
    mesmo UPDATE, evitando um segundo save().
    """
    resolved_now = now or timezone.now()
    from_status = intake.status
    update_fields = ['status', 'updated_at', *extra_update_fields]

    intake.status = to_status
    stamp_field = TERMINAL_TIMESTAMP_FIELD.get(to_status)
    if stamp_field and getattr(intake, stamp_field) is None:
        setattr(intake, stamp_field, resolved_now)
        update_fields.append(stamp_field)
    if to_status == IntakeStatus.APPROVED and conversion_kind and not intake.conversion_kind:
        intake.conversion_kind = conversion_kind
        update_fields.append('conversion_kind')

    # dict.fromkeys preserva ordem e remove duplicata caso extra_update_fields
    # repita algo que ja esta na lista base.
    intake.save(update_fields=list(dict.fromkeys(update_fields)))

    log_audit_event(
        actor=actor,
        action='intake_stage_changed',
        target=intake,
        description=f'{from_status} -> {to_status}',
        metadata={'from_status': from_status, 'to_status': to_status, 'surface': surface},
    )
    return intake


def mark_intake_first_contact(*, intake, now: datetime | None = None):
    """Registra o primeiro contato (ex: convite disparado) sem mudar status.

    Idempotente: so grava na primeira chamada.
    """
    if intake.first_contacted_at is not None:
        return intake
    intake.first_contacted_at = now or timezone.now()
    intake.save(update_fields=['first_contacted_at', 'updated_at'])
    return intake


__all__ = ['TERMINAL_TIMESTAMP_FIELD', 'mark_intake_first_contact', 'transition_intake_status']
