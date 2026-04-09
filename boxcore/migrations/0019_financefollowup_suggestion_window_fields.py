from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('boxcore', '0018_financefollowup_outcome_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='financefollowup',
            name='suggestion_queue_assist_score',
            field=models.DecimalField(decimal_places=1, default=0, max_digits=5),
        ),
        migrations.AddField(
            model_name='financefollowup',
            name='suggestion_window_age_days',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='financefollowup',
            name='suggestion_window_label',
            field=models.CharField(blank=True, max_length=48),
        ),
        migrations.AddField(
            model_name='financefollowup',
            name='suggestion_window_stage',
            field=models.CharField(blank=True, db_index=True, max_length=16),
        ),
    ]
