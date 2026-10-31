import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('public_workouts', '0049_commerce_email_lookup_indexes'),
    ]

    operations = [
        migrations.CreateModel(
            name='PublicWorkoutProgramOpen',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('plan_slug', models.SlugField(blank=True, max_length=80)),
                ('device', models.CharField(
                    choices=[('mobile', 'Celular'), ('tablet', 'Tablet'), ('desktop', 'Computador'), ('unknown', 'Desconhecido')],
                    default='unknown', max_length=8,
                )),
                ('opened_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('account', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name='program_opens',
                    to='public_workouts.publicworkoutaccount',
                )),
            ],
            options={
                'ordering': ['-opened_at'],
                'indexes': [models.Index(fields=['account', 'opened_at'], name='pw_open_account_at_idx')],
            },
        ),
    ]
