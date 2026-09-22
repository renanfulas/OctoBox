# Migracao de dado (Entrega 6, Fase 4 do CORDA de escala/nutricao, ADR-3):
# popula as duas linhas de PublicWorkoutProfessional com nome e registro
# REAIS, confirmados pelo dono do produto — decisao de conteudo, nunca um
# seed automatico/placeholder.

from django.db import migrations


def seed_professionals(apps, schema_editor):
    PublicWorkoutProfessional = apps.get_model('public_workouts', 'PublicWorkoutProfessional')
    PublicWorkoutProfessional.objects.get_or_create(
        role='treino',
        defaults={
            'name': 'Renan Fulas',
            'registration_council': 'CREF',
            'registration_number': '155070-G/SP',
        },
    )
    PublicWorkoutProfessional.objects.get_or_create(
        role='nutricao',
        defaults={
            'name': 'Giovanna Fontes',
            'registration_council': 'CRN-3',
            'registration_number': '67286',
        },
    )


def remove_seeded_professionals(apps, schema_editor):
    PublicWorkoutProfessional = apps.get_model('public_workouts', 'PublicWorkoutProfessional')
    PublicWorkoutProfessional.objects.filter(
        name__in=['Renan Fulas', 'Giovanna Fontes'],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('public_workouts', '0009_nutrition_module'),
    ]

    operations = [
        migrations.RunPython(seed_professionals, remove_seeded_professionals),
    ]
