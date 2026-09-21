import uuid

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('public_workouts', '0015_subscription_contract'),
    ]

    operations = [
        migrations.CreateModel(
            name='PublicWorkoutAcquisitionSession',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('first_source', models.CharField(blank=True, max_length=80)),
                ('first_medium', models.CharField(blank=True, max_length=80)),
                ('first_campaign', models.CharField(blank=True, max_length=120)),
                ('first_referrer', models.CharField(blank=True, max_length=180)),
                ('last_source', models.CharField(blank=True, max_length=80)),
                ('last_medium', models.CharField(blank=True, max_length=80)),
                ('last_campaign', models.CharField(blank=True, max_length=120)),
                ('last_referrer', models.CharField(blank=True, max_length=180)),
                ('landing_variant', models.CharField(blank=True, max_length=40)),
                ('offer_version', models.CharField(blank=True, max_length=40)),
                ('first_seen_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('last_seen_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('account', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='public_workouts.publicworkoutaccount')),
                ('subscription', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='acquisition_session', to='public_workouts.publicworkoutsubscription')),
            ],
        ),
        migrations.CreateModel(
            name='PublicWorkoutFunnelEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('event_type', models.CharField(db_index=True, max_length=48)),
                ('tier', models.CharField(blank=True, max_length=16)),
                ('channel', models.CharField(blank=True, db_index=True, max_length=32)),
                ('source', models.CharField(blank=True, max_length=80)),
                ('medium', models.CharField(blank=True, max_length=80)),
                ('campaign', models.CharField(blank=True, max_length=120)),
                ('schema_version', models.PositiveSmallIntegerField(default=1)),
                ('client_event_id', models.UUIDField(blank=True, null=True, unique=True)),
                ('correlation_id', models.UUIDField(blank=True, db_index=True, null=True)),
                ('occurred_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('account', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='public_workouts.publicworkoutaccount')),
                ('acquisition_session', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='events', to='public_workouts.publicworkoutacquisitionsession')),
                ('subscription', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='public_workouts.publicworkoutsubscription')),
            ],
            options={'ordering': ['-occurred_at']},
        ),
    ]
