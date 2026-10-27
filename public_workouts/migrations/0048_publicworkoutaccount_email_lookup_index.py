from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('public_workouts', '0047_training_set_duration'),
    ]

    operations = [
        migrations.AddField(
            model_name='publicworkoutaccount',
            name='email_lookup_index',
            field=models.CharField(blank=True, db_index=True, default='', max_length=67),
        ),
    ]
