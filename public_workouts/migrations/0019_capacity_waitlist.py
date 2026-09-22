import django.db.models.deletion
import django.utils.timezone
import django.core.validators
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('public_workouts', '0018_delivery_outbox')]

    operations = [
        migrations.AddField(
            model_name='publicworkoutprofessional',
            name='weekly_capacity_minutes',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='publicworkoutprofessional',
            name='internal_hourly_cost',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.CreateModel(
            name='PublicWorkoutWaitlistEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(db_index=True, max_length=254)),
                ('tier', models.CharField(choices=[('essencial', 'Essencial'), ('completo', 'Completo'), ('premium', 'Premium')], db_index=True, max_length=16)),
                ('status', models.CharField(choices=[('waiting', 'Aguardando vaga'), ('invited', 'Convidado'), ('converted', 'Convertido'), ('expired', 'Expirado'), ('canceled', 'Cancelado')], db_index=True, default='waiting', max_length=16)),
                ('invite_token', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('consented_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('invited_at', models.DateTimeField(blank=True, null=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('converted_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('acquisition_session', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='waitlist_entries', to='public_workouts.publicworkoutacquisitionsession')),
            ],
            options={'ordering': ['created_at']},
        ),
        migrations.AddConstraint(
            model_name='publicworkoutwaitlistentry',
            constraint=models.UniqueConstraint(condition=models.Q(('status', 'waiting')), fields=('email', 'tier'), name='unique_waiting_public_workout_email_tier'),
        ),
    ]
