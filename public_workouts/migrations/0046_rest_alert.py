import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('public_workouts', '0045_assessment_sex_height')]

    operations = [
        migrations.CreateModel(
            name='PublicWorkoutRestAlert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('due_at', models.DateTimeField()),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Agendado'), ('sending', 'Enviando'), ('sent', 'Enviado'),
                        ('cancelled', 'Cancelado'), ('expired', 'Vencido sem envio'), ('failed', 'Falhou'),
                    ],
                    default='pending', max_length=12,
                )),
                ('revision', models.PositiveIntegerField(default=1)),
                ('exercise_label', models.CharField(blank=True, max_length=80)),
                ('set_number', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('claimed_at', models.DateTimeField(blank=True, null=True)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('last_error', models.CharField(blank=True, max_length=120)),
                ('session', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE, related_name='rest_alert',
                    to='public_workouts.publicworkouttrainingsession',
                )),
                ('subscription', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name='rest_alerts',
                    to='public_workouts.publicworkoutpushsubscription',
                )),
            ],
            options={
                'indexes': [
                    models.Index(
                        condition=models.Q(('status', 'pending')), fields=['due_at'],
                        name='pw_rest_alert_pending_idx',
                    ),
                ],
            },
        ),
    ]
