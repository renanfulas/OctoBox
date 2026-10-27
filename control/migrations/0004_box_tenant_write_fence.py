from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('control', '0003_alter_membership_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='box',
            name='write_frozen_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='box',
            name='write_freeze_reason',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
