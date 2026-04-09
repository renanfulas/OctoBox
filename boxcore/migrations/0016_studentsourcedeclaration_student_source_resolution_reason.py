from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('boxcore', '0015_student_acquisition_foundation'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='source_resolution_reason',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.CreateModel(
            name='StudentSourceDeclaration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('declared_acquisition_source', models.CharField(choices=[('referral', 'Indicacao'), ('instagram', 'Instagram'), ('walk_in', 'Passei na frente'), ('google', 'Google'), ('whatsapp', 'WhatsApp'), ('website', 'Site'), ('meta_ads', 'Anuncio Meta'), ('event', 'Evento'), ('other', 'Outro'), ('unidentified', 'Nao identificado'), ('legacy', 'Legado')], db_index=True, max_length=32)),
                ('declared_source_detail', models.CharField(blank=True, max_length=120)),
                ('declared_source_channel', models.CharField(blank=True, max_length=32)),
                ('declared_source_response_id', models.CharField(blank=True, db_index=True, max_length=120)),
                ('captured_at', models.DateTimeField(db_index=True)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('raw_payload', models.JSONField(blank=True, default=dict)),
                ('captured_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='captured_student_source_declarations', to=settings.AUTH_USER_MODEL)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='source_declarations', to='boxcore.student')),
            ],
            options={
                'ordering': ['-captured_at', '-created_at'],
            },
        ),
    ]
