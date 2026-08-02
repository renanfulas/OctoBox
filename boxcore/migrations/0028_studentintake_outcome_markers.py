# Generated manually (Docker/Postgres indisponivel na sessao) seguindo o
# padrao autogenerado do Django 6.0.6, mesmo estilo de
# 0027_payment_currency_payment_stripe_charge_id_and_more.py.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('boxcore', '0027_payment_currency_payment_stripe_charge_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentintake',
            name='conversion_kind',
            field=models.CharField(blank=True, max_length=24),
        ),
        migrations.AddField(
            model_name='studentintake',
            name='converted_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='studentintake',
            name='first_contacted_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='studentintake',
            name='rejected_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]
