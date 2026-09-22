from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('public_workouts', '0014_merge_20260920_0100'),
    ]

    operations = [
        migrations.AddField(
            model_name='publicworkoutsubscription', name='offer_version',
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddField(
            model_name='publicworkoutsubscription', name='service_policy_version',
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddField(
            model_name='publicworkoutsubscription', name='terms_version',
            field=models.CharField(blank=True, max_length=24),
        ),
        migrations.AddField(
            model_name='publicworkoutsubscription', name='privacy_version',
            field=models.CharField(blank=True, max_length=24),
        ),
        migrations.AddField(
            model_name='publicworkoutsubscription', name='guarantee_model',
            field=models.CharField(
                choices=[
                    ('refund_guarantee', 'Cobranca imediata com garantia de reembolso'),
                    ('limited_trial', 'Trial com entrega limitada'),
                    ('full_trial', 'Trial completo'),
                ],
                default='refund_guarantee', max_length=24,
            ),
        ),
        migrations.AddField(
            model_name='publicworkoutsubscription', name='contract_accepted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='publicworkoutsubscription', name='contracted_price_id',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
