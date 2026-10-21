from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('public_workouts', '0044_program_draft_base_program')]

    operations = [
        migrations.AddField(
            model_name='publicworkoutassessment',
            name='sex',
            field=models.CharField(blank=True, default='', max_length=1),
        ),
        migrations.AddField(
            model_name='publicworkoutassessment',
            name='height_cm',
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True),
        ),
    ]
