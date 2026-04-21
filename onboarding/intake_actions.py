"""
ARQUIVO: actions de quick create e fila da Central de Intake.

POR QUE ELE EXISTE:
- separa da view as mutacoes operacionais curtas do corredor de intake.

O QUE ESTE ARQUIVO FAZ:
1. cria lead ou intake rapido com atribuicao de origem.
2. registra metricas e evento da fila apos o quick create.
3. executa a action canonica da fila operacional.
4. publica atualizacao da fila para a superficie do manager.

PONTOS CRITICOS:
- qualquer mudanca aqui altera a fila, a metrica de atribuicao e o pulso operacional da central.
- side effects de stream precisam continuar alinhados ao estado salvo.
"""

from django.db import transaction

from monitoring.lead_attribution_metrics import record_lead_attribution_capture
from onboarding.attribution import (
    build_intake_attribution_payload,
    derive_operational_source,
    normalize_acquisition_channel,
)
from onboarding.models import IntakeStatus
from shared_support.manager_event_stream import publish_manager_stream_event

from .facade import run_intake_queue_action


def create_intake_quick_entry(*, actor, form, entry_kind: str):
    with transaction.atomic():
        created_entry = form.save(commit=False)
        created_entry.status = IntakeStatus.REVIEWING if entry_kind == 'intake' else IntakeStatus.NEW
        created_entry.source = derive_operational_source(
            acquisition_channel=form.cleaned_data.get('acquisition_channel', ''),
            entry_kind=entry_kind,
        )
        created_entry.raw_payload = {
            **(created_entry.raw_payload or {}),
            **build_intake_attribution_payload(
                source=created_entry.source,
                acquisition_channel=form.cleaned_data.get('acquisition_channel', ''),
                acquisition_detail=form.cleaned_data.get('acquisition_detail', ''),
                entry_kind=entry_kind,
                actor_id=getattr(actor, 'id', None),
            ),
        }
        created_entry.save()
        normalized_channel = normalize_acquisition_channel(form.cleaned_data.get('acquisition_channel'))
        record_lead_attribution_capture(
            entry_kind=entry_kind,
            operational_source=created_entry.source,
            acquisition_channel=normalized_channel,
        )
        publish_manager_stream_event(
            event_type='intake.updated',
            meta={
                'intake_id': created_entry.id,
                'action': 'quick-create',
                'status': created_entry.status,
                'entry_kind': entry_kind,
                'acquisition_channel': normalized_channel,
            },
        )
    return created_entry


def execute_intake_queue_form(*, actor, form):
    with transaction.atomic():
        result = run_intake_queue_action(
            actor=actor,
            intake_id=form.cleaned_data['intake_id'],
            action=form.cleaned_data['action'],
        )
    publish_manager_stream_event(
        event_type='intake.updated',
        meta={
            'intake_id': result.intake_id,
            'action': form.cleaned_data['action'],
            'status': result.status,
            'assigned_to_id': result.assigned_to_id,
        },
    )
    return result


__all__ = ['create_intake_quick_entry', 'execute_intake_queue_form']
