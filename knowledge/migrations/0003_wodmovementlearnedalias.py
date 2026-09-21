from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('knowledge', '0002_knowledgechunkembedding'),
    ]

    operations = [
        migrations.CreateModel(
            name='WodMovementLearnedAlias',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('raw_text_normalized', models.CharField(db_index=True, max_length=160, unique=True)),
                ('raw_text_sample', models.CharField(max_length=160)),
                ('movement_slug', models.SlugField(max_length=64)),
                ('note', models.CharField(blank=True, max_length=200)),
                ('hit_count', models.PositiveIntegerField(default=1)),
                ('last_seen_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['-hit_count', 'raw_text_normalized']},
        ),
    ]
