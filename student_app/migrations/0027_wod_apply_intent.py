from uuid import uuid4

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('boxcore', '0031_workout_program_tracks'),
        ('operations', '0012_workouttemplate_prescription_fidelity'),
        ('student_app', '0026_wod_input_draft_revision'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='WodApplyIntent',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid4, editable=False, primary_key=True, serialize=False)),
                ('target_date', models.DateField()),
                ('mode', models.CharField(max_length=16)),
                ('fingerprint', models.CharField(max_length=64)),
                ('preview_snapshot', models.JSONField(default=dict)),
                ('response_payload', models.JSONField(blank=True, default=dict)),
                ('state', models.CharField(choices=[('prepared', 'Preparada'), ('confirmed', 'Confirmada')], default='prepared', max_length=12)),
                ('expires_at', models.DateTimeField()),
                ('confirmed_at', models.DateTimeField(blank=True, null=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='wod_apply_intents', to=settings.AUTH_USER_MODEL)),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='operations.workouttemplate')),
                ('workout_program', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='boxcore.workoutprogram')),
            ],
            options={
                'indexes': [models.Index(fields=['author', 'state', 'expires_at'], name='wod_intent_author_state_exp')],
            },
        ),
    ]
