import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('public_workouts', '0020_refund_requests')]

    operations = [
        migrations.CreateModel(
            name='PublicWorkoutTestimonial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('display_name', models.CharField(max_length=80)),
                ('quote', models.TextField(max_length=600)),
                ('result_summary', models.CharField(blank=True, max_length=180)),
                ('consented_at', models.DateTimeField()),
                ('consent_version', models.CharField(max_length=24)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('published_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('account', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='public_workouts.publicworkoutaccount')),
            ],
            options={'ordering': ['-published_at', '-created_at']},
        ),
    ]
