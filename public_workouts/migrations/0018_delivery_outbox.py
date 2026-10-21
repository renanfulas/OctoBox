import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('public_workouts', '0017_work_items'),
    ]

    operations = [
        migrations.AddField(
            model_name='publicworkoutprogramdelivery',
            name='opened_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='publicworkoutprogramdelivery',
            name='attempt_count',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.CreateModel(
            name='PublicWorkoutOutboxMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('topic', models.CharField(db_index=True, max_length=48)),
                ('aggregate_type', models.CharField(max_length=32)),
                ('aggregate_id', models.CharField(max_length=64)),
                ('version', models.PositiveIntegerField(default=1)),
                ('idempotency_key', models.CharField(max_length=160, unique=True)),
                ('payload', models.JSONField(blank=True, default=dict)),
                ('status', models.CharField(choices=[('pending', 'Pendente'), ('processing', 'Processando'), ('sent', 'Enviada'), ('dead', 'Falha definitiva')], db_index=True, default='pending', max_length=16)),
                ('attempt_count', models.PositiveSmallIntegerField(default=0)),
                ('next_attempt_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('last_error', models.CharField(blank=True, max_length=255)),
                ('processing_started_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['next_attempt_at', 'created_at']},
        ),
        migrations.CreateModel(
            name='PublicWorkoutMealPlanDelivery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attempted_at', models.DateTimeField(blank=True, null=True)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('opened_at', models.DateTimeField(blank=True, null=True)),
                ('attempt_count', models.PositiveSmallIntegerField(default=0)),
                ('last_error', models.CharField(blank=True, max_length=255)),
                ('meal_plan', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='delivery', to='public_workouts.publicworkoutmealplan')),
            ],
        ),
    ]
