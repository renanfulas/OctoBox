from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('public_workouts', '0012_program_delivery')]
    operations = [
        migrations.AddField(
            model_name='publicworkoutsubscription', name='requires_login',
            field=models.BooleanField(default=False),
        ),
    ]
