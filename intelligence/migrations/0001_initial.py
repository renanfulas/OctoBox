# Generated manually (Docker/Postgres indisponivel na sessao) seguindo o
# padrao autogerado do Django 6.0.6, mesmo estilo de
# quick_sales/migrations/0001_initial.py.

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='LeadChannelDailyFact',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('window_start', models.DateField(db_index=True)),
                ('window_end', models.DateField()),
                ('channel', models.CharField(blank=True, db_index=True, max_length=32)),
                (
                    'provenance',
                    models.CharField(
                        choices=[
                            ('declared', 'Declarado'),
                            ('confirmed', 'Confirmado'),
                            ('legacy_inferred', 'Inferido de legado'),
                            ('missing', 'Sem atribuicao'),
                        ],
                        max_length=24,
                    ),
                ),
                ('captured_total', models.PositiveIntegerField(default=0)),
                ('converted_total', models.PositiveIntegerField(default=0)),
                ('rejected_total', models.PositiveIntegerField(default=0)),
                ('open_total', models.PositiveIntegerField(default=0)),
                ('median_days_to_conversion', models.DecimalField(blank=True, decimal_places=1, max_digits=6, null=True)),
                ('rule_version', models.CharField(max_length=32)),
                ('computed_at', models.DateTimeField(db_index=True)),
                ('input_window', models.CharField(max_length=24)),
            ],
            options={
                'ordering': ['-window_start', 'channel'],
            },
        ),
        migrations.AddIndex(
            model_name='leadchanneldailyfact',
            index=models.Index(fields=['window_start', 'channel'], name='lead_channel_fact_window_idx'),
        ),
        migrations.AddConstraint(
            model_name='leadchanneldailyfact',
            constraint=models.UniqueConstraint(
                fields=('window_start', 'channel', 'provenance', 'rule_version'),
                name='unique_lead_channel_fact_cell',
            ),
        ),
    ]
