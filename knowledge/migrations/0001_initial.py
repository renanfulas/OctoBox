from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='KnowledgeDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('path', models.CharField(max_length=512, unique=True)),
                ('title', models.CharField(blank=True, max_length=255)),
                ('source_kind', models.CharField(choices=[('readme', 'README'), ('doc', 'Documento'), ('code', 'Codigo'), ('test', 'Teste'), ('template', 'Template'), ('frontend', 'Front-end'), ('spec', 'Spec'), ('other', 'Outro')], db_index=True, max_length=24)),
                ('authority_score', models.PositiveIntegerField(db_index=True, default=50)),
                ('checksum', models.CharField(db_index=True, max_length=40)),
                ('line_count', models.PositiveIntegerField(default=0)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('last_indexed_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={'ordering': ['path']},
        ),
        migrations.CreateModel(
            name='KnowledgeChunk',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ordinal', models.PositiveIntegerField()),
                ('heading', models.CharField(blank=True, max_length=255)),
                ('content', models.TextField()),
                ('content_preview', models.CharField(blank=True, max_length=280)),
                ('token_count', models.PositiveIntegerField(default=0)),
                ('start_line', models.PositiveIntegerField(default=1)),
                ('end_line', models.PositiveIntegerField(default=1)),
                ('checksum', models.CharField(db_index=True, max_length=40)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chunks', to='knowledge.knowledgedocument')),
            ],
            options={'ordering': ['document__path', 'ordinal']},
        ),
        migrations.AddConstraint(
            model_name='knowledgechunk',
            constraint=models.UniqueConstraint(fields=('document', 'ordinal'), name='unique_knowledge_chunk_document_ordinal'),
        ),
    ]

