from uuid import uuid4

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('boxcore', '0031_workout_program_tracks'),
        ('student_app', '0025_movement_demo_video_url'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='weeklywodplan',
            name='revision',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.CreateModel(
            name='WodInputDraft',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid4, editable=False, primary_key=True, serialize=False)),
                ('scope_kind', models.CharField(choices=[('daily', 'Diário'), ('weekly', 'Semanal')], max_length=8)),
                ('scope_key', models.CharField(max_length=96)),
                ('week_start', models.DateField(blank=True, null=True)),
                ('source_text', models.TextField(blank=True)),
                ('version', models.PositiveIntegerField(default=1)),
                ('parser_version', models.CharField(default='wod-input-v1', max_length=32)),
                ('create_request_id', models.UUIDField()),
                ('last_request_id', models.UUIDField(blank=True, null=True)),
                ('state', models.CharField(choices=[('active', 'Ativo'), ('discarded', 'Descartado'), ('expired', 'Expirado')], default='active', max_length=12)),
                ('expires_at', models.DateTimeField(db_index=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='wod_input_drafts', to=settings.AUTH_USER_MODEL)),
                ('session', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='input_drafts', to='boxcore.classsession')),
                ('weekly_plan', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='input_drafts', to='student_app.weeklywodplan')),
                ('workout_program', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='wod_input_drafts', to='boxcore.workoutprogram')),
            ],
            options={
                'indexes': [models.Index(fields=['author', 'state', 'expires_at'], name='wod_draft_author_state_exp')],
                'constraints': [
                    models.UniqueConstraint(condition=models.Q(state='active'), fields=('author', 'scope_key'), name='wod_draft_active_author_scope'),
                    models.UniqueConstraint(fields=('author', 'create_request_id'), name='wod_draft_author_request'),
                ],
            },
        ),
    ]
