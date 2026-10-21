from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('public_workouts', '0032_load_log_achievement')]

    operations = [
        migrations.AddField(
            model_name='publicworkoutsubscription',
            name='custom_monthly_price',
            field=models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True),
        ),
    ]
