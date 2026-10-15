from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):
    dependencies = [('public_workouts', '0039_checkout_lead')]

    operations = [
        migrations.CreateModel(
            name='PublicWorkoutTrainingSession',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('plan_slug', models.SlugField(db_index=True, max_length=80)),
                ('day_id', models.CharField(max_length=32)),
                ('started_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('completed_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('movement_count', models.PositiveSmallIntegerField(default=0)),
                ('completed_set_count', models.PositiveSmallIntegerField(default=0)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='training_sessions', to='public_workouts.publicworkoutaccount')),
            ],
            options={'ordering': ['-started_at']},
        ),
        migrations.AddIndex(
            model_name='publicworkouttrainingsession',
            index=models.Index(fields=['plan_slug', 'started_at'], name='pw_session_plan_start_idx'),
        ),
        migrations.CreateModel(
            name='PublicWorkoutTrainingSet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('movement_index', models.PositiveSmallIntegerField()),
                ('movement_slug', models.SlugField(max_length=80)),
                ('set_number', models.PositiveSmallIntegerField()),
                ('set_role', models.CharField(choices=[('warmup', 'Aquecimento'), ('feeder', 'Aproximação'), ('top_set', 'Série principal'), ('max_set', 'Esforço máximo'), ('legacy_unknown', 'Histórico')], max_length=16)),
                ('weight_kg', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('reps', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('rir', models.DecimalField(blank=True, decimal_places=1, max_digits=3, null=True)),
                ('completed_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sets', to='public_workouts.publicworkouttrainingsession')),
            ],
            options={'ordering': ['session_id', 'movement_index', 'set_number']},
        ),
        migrations.AddConstraint(
            model_name='publicworkouttrainingset',
            constraint=models.UniqueConstraint(fields=('session', 'movement_index', 'set_number'), name='pw_training_set_uniq'),
        ),
        migrations.CreateModel(
            name='PublicWorkoutPushSubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('endpoint', models.URLField(max_length=2048, unique=True)),
                ('subscription', models.JSONField(default=dict)),
                ('user_agent', models.CharField(blank=True, max_length=255)),
                ('revoked_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('last_error', models.CharField(blank=True, max_length=120)),
                ('last_push_sent_at', models.DateTimeField(blank=True, null=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='push_subscriptions', to='public_workouts.publicworkoutaccount')),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
