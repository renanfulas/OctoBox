from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('public_workouts', '0043_guided_training_set_decisions')]

    operations = [
        migrations.AddField(
            model_name='publicworkoutprogramdraft',
            name='base_program',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name='revision_drafts', to='public_workouts.publicworkoutprogram',
            ),
        ),
    ]
