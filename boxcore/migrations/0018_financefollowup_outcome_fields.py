from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('boxcore', '0017_financefollowup'),
    ]

    operations = [
        migrations.AddField(
            model_name='financefollowup',
            name='outcome_checked_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='financefollowup',
            name='outcome_reason',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name='financefollowup',
            name='outcome_status',
            field=models.CharField(
                choices=[('pending', 'Pendente'), ('succeeded', 'Bem-sucedido'), ('failed', 'Falhou'), ('expired', 'Expirado')],
                db_index=True,
                default='pending',
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name='financefollowup',
            name='outcome_window',
            field=models.CharField(default='7d', max_length=16),
        ),
    ]
