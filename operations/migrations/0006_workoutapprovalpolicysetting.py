from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('operations', '0005_workouttemplate_is_trusted'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkoutApprovalPolicySetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('box_id', models.PositiveIntegerField(db_index=True, unique=True)),
                ('approval_policy', models.CharField(choices=[('strict', 'Aprovacao obrigatoria'), ('trusted_template', 'Template confiavel publica direto'), ('coach_autonomy', 'Coach confiavel publica direto')], default='strict', max_length=32)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='workout_approval_policies_updated', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['box_id'],
            },
        ),
    ]
