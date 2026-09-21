import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('public_workouts', '0016_acquisition_and_funnel_events'),
    ]

    operations = [
        migrations.CreateModel(
            name='PublicWorkoutWorkItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_type', models.CharField(choices=[('training_program', 'Montar treino'), ('nutrition_plan', 'Montar plano nutricional'), ('training_review', 'Revisao de treino'), ('nutrition_review', 'Revisao nutricional'), ('customer_success_contact', 'Contato de acompanhamento')], max_length=32)),
                ('cycle_key', models.CharField(max_length=64)),
                ('status', models.CharField(choices=[('open', 'Aberto'), ('in_progress', 'Em andamento'), ('blocked', 'Bloqueado'), ('done', 'Concluido'), ('canceled', 'Cancelado')], db_index=True, default='open', max_length=16)),
                ('priority', models.PositiveSmallIntegerField(db_index=True, default=100)),
                ('estimated_effort_minutes', models.PositiveSmallIntegerField(default=30)),
                ('actual_effort_minutes', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('due_at', models.DateTimeField(db_index=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('blocked_reason', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='work_items', to='public_workouts.publicworkoutaccount')),
                ('assigned_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='work_items', to='public_workouts.publicworkoutprofessional')),
                ('subscription', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='work_items', to='public_workouts.publicworkoutsubscription')),
            ],
            options={
                'ordering': ['priority', 'due_at', 'created_at'],
                'constraints': [models.UniqueConstraint(fields=('subscription', 'item_type', 'cycle_key'), name='unique_public_workout_work_item_cycle')],
            },
        ),
    ]
