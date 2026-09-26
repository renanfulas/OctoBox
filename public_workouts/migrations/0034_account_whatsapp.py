from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('public_workouts', '0033_subscription_custom_monthly_price')]

    operations = [
        migrations.AddField(
            model_name='publicworkoutaccount',
            name='whatsapp',
            field=models.CharField(blank=True, max_length=20),
        ),
    ]
