from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('student_app', '0019_movementlibrary'),
    ]

    operations = [
        migrations.CreateModel(
            name='WodGenerationCreditLedger',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('period_start', models.DateField(unique=True)),
                ('free_credits_total', models.PositiveSmallIntegerField(default=2)),
                ('free_credits_used', models.PositiveSmallIntegerField(default=0)),
                ('purchased_credits_available', models.PositiveSmallIntegerField(default=0)),
            ],
            options={
                'verbose_name': 'Cota de Geracao de Treino (Haiku)',
                'verbose_name_plural': 'Cotas de Geracao de Treino (Haiku)',
                'ordering': ['-period_start'],
            },
        ),
    ]
