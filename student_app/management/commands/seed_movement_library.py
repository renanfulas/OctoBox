"""
COMANDO: seed_movement_library

POR QUE EXISTE:
- Popula MovementLibrary com os movimentos mais comuns do CrossFit e seus links
  de referencia no crossfit.com. Idempotente: usa update_or_create por slug.

USO:
    python manage.py seed_movement_library
    python manage.py seed_movement_library --dry-run   # imprime sem salvar

PONTOS CRITICOS:
- Slugs devem bater com movement_slug usado nos payloads do SmartPlan.
- reference_url aponta para crossfit.com/movement/<slug> quando disponivel.
- Nao sobrescreve reference_url manualmente editada: use o admin para isso.
"""

from django.core.management.base import BaseCommand

from student_app.models import MovementLibrary


MOVEMENTS = [
    # Levantamentos olimpicos
    {'slug': 'clean', 'label_pt': 'Clean', 'label_en': 'Clean', 'reference_url': 'https://www.crossfit.com/essentials/the-clean'},
    {'slug': 'clean-and-jerk', 'label_pt': 'Clean and Jerk', 'label_en': 'Clean and Jerk', 'reference_url': 'https://www.crossfit.com/essentials/the-clean-and-jerk'},
    {'slug': 'snatch', 'label_pt': 'Snatch', 'label_en': 'Snatch', 'reference_url': 'https://www.crossfit.com/essentials/the-snatch'},
    {'slug': 'power-clean', 'label_pt': 'Power Clean', 'label_en': 'Power Clean', 'reference_url': 'https://www.crossfit.com/essentials/the-power-clean'},
    {'slug': 'power-snatch', 'label_pt': 'Power Snatch', 'label_en': 'Power Snatch', 'reference_url': ''},
    {'slug': 'hang-clean', 'label_pt': 'Hang Clean', 'label_en': 'Hang Clean', 'reference_url': ''},
    {'slug': 'hang-power-clean', 'label_pt': 'Hang Power Clean', 'label_en': 'Hang Power Clean', 'reference_url': ''},
    {'slug': 'hang-snatch', 'label_pt': 'Hang Snatch', 'label_en': 'Hang Snatch', 'reference_url': ''},
    # Press / overhead
    {'slug': 'overhead-press', 'label_pt': 'Overhead Press', 'label_en': 'Overhead Press (Strict Press)', 'reference_url': 'https://www.crossfit.com/essentials/the-press'},
    {'slug': 'push-press', 'label_pt': 'Push Press', 'label_en': 'Push Press', 'reference_url': 'https://www.crossfit.com/essentials/the-push-press'},
    {'slug': 'push-jerk', 'label_pt': 'Push Jerk', 'label_en': 'Push Jerk', 'reference_url': 'https://www.crossfit.com/essentials/the-push-jerk'},
    {'slug': 'split-jerk', 'label_pt': 'Split Jerk', 'label_en': 'Split Jerk', 'reference_url': ''},
    {'slug': 'thruster', 'label_pt': 'Thruster', 'label_en': 'Thruster', 'reference_url': 'https://www.crossfit.com/essentials/the-thruster'},
    # Agachamentos
    {'slug': 'back-squat', 'label_pt': 'Agachamento Costas', 'label_en': 'Back Squat', 'reference_url': 'https://www.crossfit.com/essentials/the-back-squat'},
    {'slug': 'front-squat', 'label_pt': 'Agachamento Frontal', 'label_en': 'Front Squat', 'reference_url': 'https://www.crossfit.com/essentials/the-front-squat'},
    {'slug': 'overhead-squat', 'label_pt': 'Agachamento Overhead', 'label_en': 'Overhead Squat', 'reference_url': 'https://www.crossfit.com/essentials/the-overhead-squat'},
    {'slug': 'air-squat', 'label_pt': 'Agachamento Livre', 'label_en': 'Air Squat', 'reference_url': 'https://www.crossfit.com/essentials/the-air-squat'},
    {'slug': 'wall-ball', 'label_pt': 'Wall Ball', 'label_en': 'Wall Ball Shot', 'reference_url': 'https://www.crossfit.com/essentials/the-wall-ball-shot'},
    # Puxadas / barras
    {'slug': 'deadlift', 'label_pt': 'Levantamento Terra', 'label_en': 'Deadlift', 'reference_url': 'https://www.crossfit.com/essentials/the-deadlift'},
    {'slug': 'sumo-deadlift-high-pull', 'label_pt': 'Sumo Deadlift High Pull', 'label_en': 'Sumo Deadlift High Pull', 'reference_url': 'https://www.crossfit.com/essentials/the-sumo-deadlift-high-pull'},
    {'slug': 'pull-up', 'label_pt': 'Barra Fixa', 'label_en': 'Pull-up', 'reference_url': 'https://www.crossfit.com/essentials/the-pull-up'},
    {'slug': 'chest-to-bar', 'label_pt': 'Chest-to-Bar', 'label_en': 'Chest-to-Bar Pull-up', 'reference_url': ''},
    {'slug': 'muscle-up', 'label_pt': 'Muscle-up', 'label_en': 'Muscle-up (Bar)', 'reference_url': 'https://www.crossfit.com/essentials/the-muscle-up'},
    {'slug': 'ring-muscle-up', 'label_pt': 'Muscle-up nas Argolas', 'label_en': 'Ring Muscle-up', 'reference_url': ''},
    {'slug': 'toes-to-bar', 'label_pt': 'Toes-to-Bar', 'label_en': 'Toes-to-Bar', 'reference_url': 'https://www.crossfit.com/essentials/toes-to-bar'},
    {'slug': 'ring-row', 'label_pt': 'Ring Row', 'label_en': 'Ring Row', 'reference_url': ''},
    # Empurradas / solo
    {'slug': 'push-up', 'label_pt': 'Flexao de Bracos', 'label_en': 'Push-up', 'reference_url': 'https://www.crossfit.com/essentials/the-push-up'},
    {'slug': 'handstand-push-up', 'label_pt': 'Flexao Invertida (HSPU)', 'label_en': 'Handstand Push-up', 'reference_url': 'https://www.crossfit.com/essentials/the-handstand-push-up'},
    {'slug': 'handstand-walk', 'label_pt': 'Caminhada Invertida', 'label_en': 'Handstand Walk', 'reference_url': ''},
    {'slug': 'dip', 'label_pt': 'Mergulho (Dip)', 'label_en': 'Ring Dip', 'reference_url': 'https://www.crossfit.com/essentials/the-ring-dip'},
    # Cardio / saltos
    {'slug': 'box-jump', 'label_pt': 'Salto na Caixa', 'label_en': 'Box Jump', 'reference_url': 'https://www.crossfit.com/essentials/the-box-jump'},
    {'slug': 'double-under', 'label_pt': 'Double Under', 'label_en': 'Double Under', 'reference_url': 'https://www.crossfit.com/essentials/the-double-under'},
    {'slug': 'single-under', 'label_pt': 'Single Under', 'label_en': 'Single Under', 'reference_url': ''},
    {'slug': 'burpee', 'label_pt': 'Burpee', 'label_en': 'Burpee', 'reference_url': 'https://www.crossfit.com/essentials/the-burpee'},
    {'slug': 'box-step-up', 'label_pt': 'Step-up na Caixa', 'label_en': 'Box Step-up', 'reference_url': ''},
    # Cardio com equipamento
    {'slug': 'row', 'label_pt': 'Remo (Rower)', 'label_en': 'Row (Rower)', 'reference_url': ''},
    {'slug': 'assault-bike', 'label_pt': 'Bike (Assault)', 'label_en': 'Assault Bike', 'reference_url': ''},
    {'slug': 'ski-erg', 'label_pt': 'Ski Erg', 'label_en': 'Ski Erg', 'reference_url': ''},
    {'slug': 'run', 'label_pt': 'Corrida', 'label_en': 'Run', 'reference_url': ''},
    # Kettlebell
    {'slug': 'kettlebell-swing', 'label_pt': 'Kettlebell Swing', 'label_en': 'Kettlebell Swing', 'reference_url': 'https://www.crossfit.com/essentials/the-kettlebell-swing'},
    {'slug': 'turkish-get-up', 'label_pt': 'Turkish Get-up', 'label_en': 'Turkish Get-up', 'reference_url': ''},
    # Core
    {'slug': 'ghd-sit-up', 'label_pt': 'GHD Sit-up', 'label_en': 'GHD Sit-up', 'reference_url': 'https://www.crossfit.com/essentials/the-ghd-sit-up'},
    {'slug': 'sit-up', 'label_pt': 'Abdominal', 'label_en': 'Sit-up', 'reference_url': ''},
    {'slug': 'back-extension', 'label_pt': 'Extensao de Lombar', 'label_en': 'Back Extension (GHD)', 'reference_url': 'https://www.crossfit.com/essentials/the-back-extension'},
    {'slug': 'plank', 'label_pt': 'Prancha', 'label_en': 'Plank', 'reference_url': ''},
]


class Command(BaseCommand):
    help = 'Popula MovementLibrary com movimentos comuns do CrossFit (idempotente).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Imprime os movimentos sem salvar no banco.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        created_count = 0
        updated_count = 0

        for movement in MOVEMENTS:
            if dry_run:
                self.stdout.write(f"  [{movement['slug']}] {movement['label_pt']}")
                continue

            _, created = MovementLibrary.objects.update_or_create(
                slug=movement['slug'],
                defaults={
                    'label_pt': movement['label_pt'],
                    'label_en': movement['label_en'],
                    'reference_url': movement['reference_url'],
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'\nDRY RUN — {len(MOVEMENTS)} movimentos listados, nenhum salvo.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'MovementLibrary: {created_count} criados, {updated_count} atualizados.'
            ))
