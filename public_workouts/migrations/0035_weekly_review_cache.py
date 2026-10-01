import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('public_workouts', '0034_account_whatsapp')]

    operations = [
        migrations.CreateModel(
            name='PublicWorkoutWeeklyReviewCache',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('iso_week', models.CharField(db_index=True, max_length=8)),
                ('review_text', models.TextField(blank=True, null=True)),
                ('generated_at', models.DateTimeField(auto_now_add=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='weekly_review_cache_entries', to='public_workouts.publicworkoutaccount')),
            ],
        ),
        migrations.AddConstraint(
            model_name='publicworkoutweeklyreviewcache',
            constraint=models.UniqueConstraint(fields=('account', 'iso_week'), name='unique_weekly_review_cache_per_week'),
        ),
    ]
