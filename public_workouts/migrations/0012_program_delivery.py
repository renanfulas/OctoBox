from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('public_workouts', '0011_nutrition_profile_consent')]

    operations = [
        migrations.CreateModel(
            name='PublicWorkoutProgramDelivery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attempted_at', models.DateTimeField(blank=True, null=True)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('last_error', models.CharField(blank=True, max_length=255)),
                ('program', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='delivery', to='public_workouts.publicworkoutprogram')),
            ],
        ),
    ]
