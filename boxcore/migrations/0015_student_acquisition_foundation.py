from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('boxcore', '0014_reopen_pending_matched_intakes'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='acquisition_source',
            field=models.CharField(blank=True, choices=[('referral', 'Indicacao'), ('instagram', 'Instagram'), ('walk_in', 'Passei na frente'), ('google', 'Google'), ('whatsapp', 'WhatsApp'), ('website', 'Site'), ('meta_ads', 'Anuncio Meta'), ('event', 'Evento'), ('other', 'Outro'), ('unidentified', 'Nao identificado'), ('legacy', 'Legado')], db_index=True, max_length=32),
        ),
        migrations.AddField(
            model_name='student',
            name='acquisition_source_detail',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='student',
            name='resolved_acquisition_source',
            field=models.CharField(blank=True, choices=[('referral', 'Indicacao'), ('instagram', 'Instagram'), ('walk_in', 'Passei na frente'), ('google', 'Google'), ('whatsapp', 'WhatsApp'), ('website', 'Site'), ('meta_ads', 'Anuncio Meta'), ('event', 'Evento'), ('other', 'Outro'), ('unidentified', 'Nao identificado'), ('legacy', 'Legado')], db_index=True, max_length=32),
        ),
        migrations.AddField(
            model_name='student',
            name='resolved_source_detail',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='student',
            name='source_captured_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='student',
            name='source_captured_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name='captured_students', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='student',
            name='source_confidence',
            field=models.CharField(choices=[('unknown', 'Desconhecida'), ('high', 'Alta'), ('medium', 'Media'), ('low', 'Baixa')], default='unknown', max_length=16),
        ),
        migrations.AddField(
            model_name='student',
            name='source_conflict_flag',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='student',
            name='source_resolution_method',
            field=models.CharField(blank=True, choices=[('intake_auto', 'Intake automatico'), ('manual_form', 'Formulario manual'), ('manual_review', 'Revisao manual'), ('declared_only', 'Somente declarado'), ('legacy', 'Legado')], max_length=24),
        ),
    ]
