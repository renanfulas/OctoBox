"""
ARQUIVO: migracao de endurecimento para integracoes e payloads estruturados.

POR QUE ELE EXISTE:
- Converte payloads brutos em JSON estruturado e adiciona unicidade real para identidades externas do WhatsApp.

O QUE ESTE ARQUIVO FAZ:
1. Converte raw_payload legado para JSON seguro em intake e logs de mensagem.
2. Adiciona external_contact_id ao contato de WhatsApp.
3. Cria constraints condicionais para evitar duplicidade de ids externos nao vazios.

PONTOS CRITICOS:
- A conversao precisa tolerar payload legado salvo como texto ou repr de dict.
"""

import ast
import json

from django.db import migrations, models


def _to_structured_payload(raw_value):
    if raw_value in (None, '', {}):
        return {}
    if isinstance(raw_value, dict):
        return raw_value
    if isinstance(raw_value, list):
        return {'items': raw_value}
    if isinstance(raw_value, str):
        stripped = raw_value.strip()
        if not stripped:
            return {}
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(stripped)
            except (ValueError, SyntaxError):
                continue
            if isinstance(parsed, dict):
                return parsed
            if isinstance(parsed, list):
                return {'items': parsed}
            return {'value': parsed}
        return {'raw_text': stripped}
    return {'value': str(raw_value)}


def convert_legacy_payloads(apps, schema_editor):
    StudentIntake = apps.get_model('boxcore', 'StudentIntake')
    WhatsAppMessageLog = apps.get_model('boxcore', 'WhatsAppMessageLog')

    for intake in StudentIntake.objects.all().only('id', 'raw_payload'):
        StudentIntake.objects.filter(pk=intake.pk).update(raw_payload=json.dumps(_to_structured_payload(intake.raw_payload)))

    for message_log in WhatsAppMessageLog.objects.all().only('id', 'raw_payload'):
        WhatsAppMessageLog.objects.filter(pk=message_log.pk).update(
            raw_payload=json.dumps(_to_structured_payload(message_log.raw_payload))
        )


class Migration(migrations.Migration):

    dependencies = [
        ('boxcore', '0005_payment_schedule_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='whatsappcontact',
            name='external_contact_id',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.RunPython(convert_legacy_payloads, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='studentintake',
            name='raw_payload',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name='whatsappmessagelog',
            name='raw_payload',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddConstraint(
            model_name='whatsappcontact',
            constraint=models.UniqueConstraint(
                condition=~models.Q(external_contact_id=''),
                fields=('external_contact_id',),
                name='unique_non_blank_whatsapp_external_contact_id',
            ),
        ),
        migrations.AddConstraint(
            model_name='whatsappmessagelog',
            constraint=models.UniqueConstraint(
                condition=~models.Q(external_message_id=''),
                fields=('external_message_id',),
                name='unique_non_blank_whatsapp_external_message_id',
            ),
        ),
    ]