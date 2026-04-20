from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student_app', '0011_sessionworkoutrmgapaction'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sessionworkoutrmgapaction',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='sessionworkoutrmgapaction',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
