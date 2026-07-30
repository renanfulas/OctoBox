# Migration de dados: recupera converted_at e first_contacted_at a partir de
# AuditEvent ja existentes, para o historico nao ficar todo com censura a
# direita so por ter nascido antes da Onda 4 do plano de ML de leads.
#
# rejected_at NAO e recuperavel: rejeicao nunca deixou rastro datado antes
# desta onda (ver achado M18/A3 da auditoria de leads 2026-07-28). Fica null
# para intakes rejeitados antes desta migration — nao ha fonte historica.
#
# Idempotente e seguro para rodar mais de uma vez (so preenche onde ainda
# esta null). Reverso e no-op: dado recuperado nao precisa ser apagado.

from django.db import migrations


def backfill_outcome_markers(apps, schema_editor):
    StudentIntake = apps.get_model('boxcore', 'StudentIntake')
    AuditEvent = apps.get_model('boxcore', 'AuditEvent')

    converted_events = (
        AuditEvent.objects.filter(action='student_intake_converted', target_model='studentintake')
        .exclude(target_id='')
        .only('target_id', 'created_at')
        .order_by('created_at')
    )
    earliest_converted_at_by_intake_id = {}
    for event in converted_events:
        try:
            intake_id = int(event.target_id)
        except (TypeError, ValueError):
            continue
        earliest_converted_at_by_intake_id.setdefault(intake_id, event.created_at)

    for intake_id, converted_at in earliest_converted_at_by_intake_id.items():
        StudentIntake.objects.filter(pk=intake_id, converted_at__isnull=True).update(
            converted_at=converted_at,
            conversion_kind='enrollment',
        )

    handoff_events = (
        AuditEvent.objects.filter(action='student_onboarding.imported_lead_invite.whatsapp_handoff_opened')
        .only('metadata', 'created_at')
        .order_by('created_at')
    )
    earliest_contact_at_by_intake_id = {}
    for event in handoff_events:
        raw_intake_id = (event.metadata or {}).get('intake_id')
        if raw_intake_id is None:
            continue
        try:
            intake_id = int(raw_intake_id)
        except (TypeError, ValueError):
            continue
        earliest_contact_at_by_intake_id.setdefault(intake_id, event.created_at)

    for intake_id, first_contacted_at in earliest_contact_at_by_intake_id.items():
        StudentIntake.objects.filter(pk=intake_id, first_contacted_at__isnull=True).update(
            first_contacted_at=first_contacted_at,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('boxcore', '0028_studentintake_outcome_markers'),
    ]

    operations = [
        migrations.RunPython(backfill_outcome_markers, reverse_code=migrations.RunPython.noop, elidable=False),
    ]
