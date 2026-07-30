# Generated manually (Docker/Postgres indisponivel na sessao) seguindo o
# padrao autogerado do Django 6.0.6, mesmo estilo de
# intelligence/migrations/0001_initial.py.

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='NetworkChannelAggregate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('box_slug', models.CharField(db_index=True, max_length=64)),
                ('box_cohort', models.CharField(db_index=True, max_length=32)),
                ('segment_key', models.CharField(blank=True, db_index=True, max_length=64)),
                ('channel', models.CharField(db_index=True, max_length=32)),
                ('window', models.CharField(max_length=24)),
                ('captured_total', models.PositiveIntegerField()),
                ('converted_total', models.PositiveIntegerField()),
                ('retained_90d_total', models.PositiveIntegerField(default=0)),
                ('k_floor_applied', models.PositiveSmallIntegerField()),
                ('contributed_at', models.DateTimeField(db_index=True)),
            ],
            options={
                'ordering': ['-contributed_at'],
            },
        ),
        migrations.AddIndex(
            model_name='networkchannelaggregate',
            index=models.Index(fields=['box_cohort', 'channel', 'window'], name='net_channel_cohort_idx'),
        ),
        migrations.AddConstraint(
            model_name='networkchannelaggregate',
            constraint=models.UniqueConstraint(
                fields=('box_slug', 'channel', 'window'),
                name='unique_network_channel_aggregate_cell',
            ),
        ),
    ]
