from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('public_workouts', '0048_publicworkoutaccount_email_lookup_index'),
    ]

    operations = [
        migrations.AddField(
            model_name='publicworkoutcheckoutlead',
            name='email_lookup_index',
            field=models.CharField(blank=True, db_index=True, default='', max_length=67),
        ),
        migrations.AddField(
            model_name='publicworkoutwaitlistentry',
            name='email_lookup_index',
            field=models.CharField(blank=True, db_index=True, default='', max_length=67),
        ),
    ]
