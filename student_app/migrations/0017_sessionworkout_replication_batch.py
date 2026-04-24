from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('student_app', '0016_weeklywodplan_source_text_and_parsed_payload'),
    ]

    operations = [
        migrations.AddField(
            model_name='sessionworkout',
            name='replication_batch',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='session_workouts',
                to='student_app.replicationbatch',
            ),
        ),
    ]
