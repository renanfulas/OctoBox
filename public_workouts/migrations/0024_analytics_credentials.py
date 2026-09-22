from django.db import migrations, models


ANALYTICS_USERS = {
    'renan': 'pbkdf2_sha256$1200000$F5I4VTGyxIQQ3XY0S75uRN$b3g9PSCUe6l4xRuAIPCfrXqcTw6t6M162uUDTD9ZZKU=',
    'giovannafontesrios': 'pbkdf2_sha256$1200000$C46R5kyuD3y7gKDtvd7ygb$WBUXZFtXhmNDK8gkuTUAdNG4G4Sq+bDQ+bXhd3Fldac=',
}


def seed_analytics_users(apps, schema_editor):
    credential_model = apps.get_model('public_workouts', 'PublicWorkoutAnalyticsCredential')
    for username, password_hash in ANALYTICS_USERS.items():
        credential_model.objects.update_or_create(
            username=username,
            defaults={'password_hash': password_hash, 'is_active': True},
        )


def remove_analytics_users(apps, schema_editor):
    credential_model = apps.get_model('public_workouts', 'PublicWorkoutAnalyticsCredential')
    credential_model.objects.filter(username__in=ANALYTICS_USERS).delete()


class Migration(migrations.Migration):
    dependencies = [('public_workouts', '0023_campaign_spend')]

    operations = [
        migrations.CreateModel(
            name='PublicWorkoutAnalyticsCredential',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('username', models.CharField(max_length=80, unique=True)),
                ('password_hash', models.CharField(max_length=255)),
                ('is_active', models.BooleanField(default=True)),
                ('last_login_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={'ordering': ['username']},
        ),
        migrations.RunPython(seed_analytics_users, remove_analytics_users),
    ]
