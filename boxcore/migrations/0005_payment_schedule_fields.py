"""
ARQUIVO: migration 0005 de parcelamento e agrupamento de cobrancas.

POR QUE ELE EXISTE:
- permite representar pagamentos parcelados e agrupar cobrancas relacionadas no financeiro.

O QUE ESTE ARQUIVO FAZ:
1. adiciona grupo de faturamento ao pagamento.
2. adiciona numero da parcela atual.
3. adiciona total de parcelas previstas.

PONTOS CRITICOS:
- esses campos afetam leitura financeira e integracoes futuras de automacao.
- mudancas retroativas em migrations podem quebrar bancos ja aplicados.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('boxcore', '0004_student_profile_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='billing_group',
            field=models.CharField(blank=True, max_length=36),
        ),
        migrations.AddField(
            model_name='payment',
            name='installment_number',
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='payment',
            name='installment_total',
            field=models.PositiveSmallIntegerField(default=1),
        ),
    ]