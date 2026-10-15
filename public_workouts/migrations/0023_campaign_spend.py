from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    dependencies = [('public_workouts', '0022_metric_snapshots')]

    operations = [
        migrations.CreateModel(
            name='PublicWorkoutCampaignSpend',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.CharField(max_length=80)),
                ('campaign', models.CharField(max_length=120)),
                ('starts_on', models.DateField()),
                ('ends_on', models.DateField()),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])),
                ('currency', models.CharField(default='brl', max_length=3)),
                ('notes', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-starts_on', 'source', 'campaign'],
                'constraints': [
                    models.UniqueConstraint(fields=('source', 'campaign', 'starts_on', 'ends_on'), name='unique_public_workout_campaign_spend_period'),
                    models.CheckConstraint(condition=models.Q(('ends_on__gte', models.F('starts_on'))), name='public_workout_campaign_spend_valid_period'),
                ],
            },
        ),
    ]
