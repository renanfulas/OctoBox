from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('boxcore', '0003_auditevent'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='cpf',
            field=models.CharField(blank=True, max_length=14),
        ),
        migrations.AddField(
            model_name='student',
            name='gender',
            field=models.CharField(blank=True, choices=[('male', 'Masculino'), ('female', 'Feminino')], max_length=16),
        ),
        migrations.AddField(
            model_name='student',
            name='health_issue_status',
            field=models.CharField(blank=True, choices=[('yes', 'Sim'), ('no', 'Nao')], max_length=8),
        ),
        migrations.AlterField(
            model_name='student',
            name='phone',
            field=models.CharField(max_length=20, unique=True, verbose_name='WhatsApp'),
        ),
        migrations.RemoveField(
            model_name='student',
            name='emergency_contact',
        ),
        migrations.RemoveField(
            model_name='student',
            name='source',
        ),
        migrations.RemoveField(
            model_name='student',
            name='whatsapp_verified',
        ),
    ]