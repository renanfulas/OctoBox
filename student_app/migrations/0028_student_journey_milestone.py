from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('student_app', '0027_wod_apply_intent'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentJourneyMilestone',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('idempotency_key', models.CharField(max_length=64, unique=True)),
                ('journey', models.CharField(blank=True, max_length=32)),
                ('milestone', models.CharField(max_length=40)),
                ('subject_kind', models.CharField(max_length=24)),
                ('subject_key', models.CharField(max_length=100)),
                ('cohort_kind', models.CharField(max_length=24)),
                ('cohort_key', models.CharField(max_length=100)),
                ('identity_id', models.PositiveBigIntegerField(blank=True, db_index=True, null=True)),
                ('occurred_at', models.DateTimeField(db_index=True)),
                ('timezone_name', models.CharField(max_length=64)),
                ('contract_version', models.PositiveSmallIntegerField(default=1)),
            ],
            options={
                'ordering': ['occurred_at', 'id'],
                'indexes': [
                    models.Index(fields=['journey', 'milestone', 'occurred_at'], name='journey_mile_time_idx'),
                    models.Index(fields=['journey', 'cohort_kind', 'cohort_key'], name='journey_cohort_key_idx'),
                    models.Index(fields=['identity_id', 'milestone', 'occurred_at'], name='journey_identity_mile_idx'),
                ],
            },
        ),
    ]
