from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0007_workoutplannertemplatepickerevent'),
    ]

    operations = [
        migrations.CreateModel(
            name='SessionCancellationEvent',
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
                ('session_id', models.PositiveIntegerField(db_index=True)),
                ('box_root_slug', models.CharField(db_index=True, max_length=64)),
                ('copy_variant', models.CharField(default='ahead', max_length=24)),
                ('attendance_count_at_cancel', models.PositiveIntegerField(default=0)),
                ('push_sent_count', models.PositiveIntegerField(default=0)),
                ('scheduled_at', models.DateTimeField(blank=True, null=True)),
                ('session_title', models.CharField(blank=True, max_length=100)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='sessioncancellationevent',
            constraint=models.UniqueConstraint(
                fields=['session_id'],
                name='ops_session_cancel_evt_unique_session',
            ),
        ),
        migrations.AddIndex(
            model_name='sessioncancellationevent',
            index=models.Index(
                fields=['box_root_slug', 'created_at'],
                name='ops_sess_cancel_box_idx',
            ),
        ),
    ]
