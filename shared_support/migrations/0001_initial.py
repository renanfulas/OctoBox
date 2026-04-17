import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='IdempotencyKey',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(help_text='A chave unica enviada pelo cliente (ex: UUID)', max_length=255, unique=True)),
                ('response_code', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('response_data', models.JSONField(blank=True, help_text='A resposta salva para ser retornada se houver repeticao', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('locked_at', models.DateTimeField(blank=True, help_text='Usado como trava para evitar processamento simultaneo', null=True)),
                ('user', models.ForeignKey(blank=True, help_text='O usuario que fez a requisicao', null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'idempotency_keys',
                'indexes': [models.Index(fields=['key'], name='idempotency_key_0fd07b_idx')],
            },
        ),
    ]
