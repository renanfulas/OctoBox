from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('knowledge', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='KnowledgeChunkEmbedding',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('model', models.CharField(db_index=True, max_length=64)),
                ('dimensions', models.PositiveIntegerField(db_index=True, default=0)),
                ('checksum', models.CharField(db_index=True, max_length=40)),
                ('vector', models.BinaryField()),
                ('norm', models.FloatField(default=0.0)),
                ('generated_at', models.DateTimeField(db_index=True)),
                ('chunk', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='embedding', to='knowledge.knowledgechunk')),
            ],
            options={'ordering': ['chunk__document__path', 'chunk__ordinal']},
        ),
        migrations.AddIndex(
            model_name='knowledgechunkembedding',
            index=models.Index(fields=['model', 'dimensions'], name='knowledge_kn_model_0c7ca8_idx'),
        ),
    ]
