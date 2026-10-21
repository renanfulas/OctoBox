from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('public_workouts', '0028_load_log_set_role')]

    operations = [
        migrations.AddConstraint(
            model_name='publicworkoutloadlog',
            constraint=models.CheckConstraint(
                condition=models.Q(set_role__in=['warmup', 'feeder', 'top_set', 'max_set', 'legacy_unknown'])
                | models.Q(set_role__isnull=True),
                name='public_workouts_loadlog_set_role_valid_or_null',
            ),
        ),
    ]
