from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0006_workoutapprovalpolicysetting'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkoutPlannerTemplatePickerEvent',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('event_name', models.CharField(db_index=True, max_length=24)),
                ('session_id', models.PositiveIntegerField(db_index=True)),
                ('action_outcome', models.CharField(blank=True, max_length=32)),
                (
                    'actor',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name='workout_planner_template_picker_events',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'template',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name='planner_picker_events',
                        to='operations.workouttemplate',
                    ),
                ),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['event_name', 'created_at'], name='ops_tpl_evt_name_idx'),
                    models.Index(fields=['session_id', 'created_at'], name='ops_tpl_evt_sess_idx'),
                ],
            },
        ),
    ]
