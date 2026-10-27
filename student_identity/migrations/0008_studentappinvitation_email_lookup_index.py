from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student_identity', '0007_studentappinvitation_qa_seed_marker'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentappinvitation',
            name='email_lookup_index',
            field=models.CharField(blank=True, db_index=True, default='', max_length=67),
        ),
    ]
