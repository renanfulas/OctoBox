import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('public_workouts', '0019_capacity_waitlist')]

    operations = [
        migrations.CreateModel(
            name='PublicWorkoutRefundRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('requested', 'Solicitado'), ('processing', 'Processando'), ('refunded', 'Reembolsado'), ('rejected', 'Rejeitado'), ('failed', 'Falhou')], db_index=True, default='requested', max_length=16)),
                ('reason', models.TextField(blank=True)),
                ('stripe_refund_id', models.CharField(blank=True, max_length=255)),
                ('last_error', models.CharField(blank=True, max_length=255)),
                ('requested_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('payment', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='refund_requests', to='public_workouts.publicworkoutpayment')),
                ('subscription', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='refund_request', to='public_workouts.publicworkoutsubscription')),
            ],
        ),
    ]
