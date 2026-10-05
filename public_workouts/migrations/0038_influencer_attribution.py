from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('public_workouts', '0037_publicworkoutaccount_onboarding_completed_at')]

    operations = [
        migrations.AddField(
            model_name='publicworkoutacquisitionsession',
            name='partner_code',
            field=models.CharField(blank=True, db_index=True, max_length=48),
        ),
        migrations.AddField(
            model_name='publicworkoutacquisitionsession',
            name='partner_first_seen_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='publicworkoutfunnelevent',
            name='partner_code',
            field=models.CharField(blank=True, db_index=True, max_length=48),
        ),
    ]
