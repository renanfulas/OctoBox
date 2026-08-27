"""
ARQUIVO: adiciona Box.billing_event_at (guarda de ordenacao de eventos Stripe).

POR QUE ELE EXISTE:
- A Stripe nao garante ordem de entrega de webhooks, e o retry sweep interno
  (reprocess_due_stripe_webhook_events) reentrega eventos antigos por design.
- Sem um relogio por box, um invoice.payment_succeeded atrasado da assinatura
  antiga reativa um box cancelado.

NULL em boxes existentes: primeiro evento de billing que chegar carimba o valor.
Ate la a guarda e no-op (fail-open), que e o comportamento atual — nao regride nada.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('control', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='box',
            name='billing_event_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
