from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('student_app', '0013_studentappactivity_studentexercisemaxhistory'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkoutTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=120)),
                ('is_active', models.BooleanField(default=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='workout_templates_created', to=settings.AUTH_USER_MODEL)),
                ('source_workout', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='derived_templates', to='student_app.sessionworkout')),
            ],
            options={'ordering': ['name', '-created_at']},
        ),
        migrations.CreateModel(
            name='WorkoutTemplateBlock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('kind', models.CharField(choices=[('warmup', 'Aquecimento'), ('strength', 'Forca'), ('skill', 'Skill'), ('metcon', 'Metcon'), ('cooldown', 'Cooldown'), ('custom', 'Livre')], default='custom', max_length=24)),
                ('title', models.CharField(max_length=120)),
                ('notes', models.TextField(blank=True)),
                ('sort_order', models.PositiveIntegerField(default=1)),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='blocks', to='operations.workouttemplate')),
            ],
            options={'ordering': ['sort_order', 'id']},
        ),
        migrations.CreateModel(
            name='WorkoutTemplateMovement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('movement_slug', models.SlugField(max_length=64)),
                ('movement_label', models.CharField(max_length=120)),
                ('sets', models.PositiveIntegerField(blank=True, null=True)),
                ('reps', models.PositiveIntegerField(blank=True, null=True)),
                ('load_type', models.CharField(choices=[('free', 'Livre'), ('fixed_kg', 'Carga fixa'), ('percentage_of_rm', 'Percentual do RM')], default='free', max_length=32)),
                ('load_value', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('notes', models.CharField(blank=True, max_length=255)),
                ('sort_order', models.PositiveIntegerField(default=1)),
                ('block', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='movements', to='operations.workouttemplateblock')),
            ],
            options={'ordering': ['sort_order', 'id']},
        ),
    ]
