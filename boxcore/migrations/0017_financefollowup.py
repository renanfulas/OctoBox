from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('boxcore', '0016_studentsourcedeclaration_student_source_resolution_reason'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='FinanceFollowUp',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('suggestion_key', models.CharField(db_index=True, max_length=180, unique=True)),
                ('source_surface', models.CharField(db_index=True, default='finance_queue', max_length=32)),
                ('signal_bucket', models.CharField(blank=True, db_index=True, max_length=32)),
                ('recommended_action', models.CharField(db_index=True, max_length=64)),
                ('priority_rank', models.PositiveSmallIntegerField(default=0)),
                ('confidence', models.CharField(blank=True, max_length=16)),
                ('prediction_window', models.CharField(blank=True, max_length=32)),
                ('rule_version', models.CharField(blank=True, max_length=32)),
                ('status', models.CharField(choices=[('suggested', 'Sugerido'), ('realized', 'Realizado'), ('superseded', 'Substituido')], db_index=True, default='suggested', max_length=16)),
                ('suggested_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('resolved_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('realized_action_kind', models.CharField(blank=True, max_length=32)),
                ('payload', models.JSONField(blank=True, default=dict)),
                ('enrollment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='finance_follow_ups', to='boxcore.enrollment')),
                ('payment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='finance_follow_ups', to='boxcore.payment')),
                ('resolved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='resolved_finance_follow_ups', to=settings.AUTH_USER_MODEL)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='finance_follow_ups', to='boxcore.student')),
            ],
            options={
                'ordering': ['status', 'priority_rank', '-suggested_at'],
            },
        ),
    ]
