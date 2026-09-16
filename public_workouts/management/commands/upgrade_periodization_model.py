"""
COMANDO: upgrade_periodization_model

POR QUE EXISTE:
- Onda B3+ do CORDA (docs/plans/public-workouts-produtizacao-corda.md,
  "Periodização canônica") — acrescenta `periodization.weeks` (vocabulário
  fechado, ver `public_workouts/periodization.py::PHASE_PROFILES`) ao
  payload JÁ PUBLICADO de um cliente, mapeando o `chart` livre que ele já
  tem pras 6 fases canônicas. Aditivo (schema.py): `chart`/`weeks_table`
  continuam intactos, `weeks` só se soma.
- Escopo desta fatia é SÓ a Juliana (prova de conceito, pedido do Renan) —
  o mapeamento pras outras 9 clientes é curadoria manual (o `focus` de cada
  uma usa vocabulário próprio, não dá pra automatizar sem inventar
  correspondência — ver "Achado de pesquisa" no plano), feita uma de cada
  vez quando fizer sentido migrá-las.

USO:
    python manage.py upgrade_periodization_model --dry-run --slug=juliana
    python manage.py upgrade_periodization_model --slug=juliana

PONTOS CRÍTICOS:
- Lê o payload JÁ PUBLICADO (`services.get_active_program`), nunca o HTML
  legado de novo — `weeks` é curadoria em cima do que já está no ar, não
  uma nova extração.
- `CURATED_WEEKS_MAPPING` é o mapeamento manual REAL (conferido contra o
  `chart` publicado da Juliana) do rótulo livre de cada semana pro
  `phase_type` canônico mais próximo — decisão de leitura humana, não
  adivinhação automática (por isso só cobre quem já foi revisado).
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from public_workouts import schema
from public_workouts.services import get_active_program, publish_program

# Mapeamento manual, conferido contra o `chart` real já publicado de cada
# cliente (S1..S6 na ordem de aparição). Só Juliana nesta fatia (ver
# docstring do módulo) -- adicionar uma cliente nova aqui é decisão
# separada, uma de cada vez.
CURATED_WEEKS_MAPPING = {
    'juliana': [
        {'week_number': 1, 'phase_type': 'adaptation'},
        {'week_number': 2, 'phase_type': 'volume'},
        {'week_number': 3, 'phase_type': 'strength_hypertrophy'},
        {'week_number': 4, 'phase_type': 'intensity'},
        {'week_number': 5, 'phase_type': 'peak'},
        {'week_number': 6, 'phase_type': 'deload'},
    ],
}


class Command(BaseCommand):
    help = (
        'Acrescenta periodization.weeks (modelo canonico) ao payload ja publicado '
        'de um cliente -- so Juliana nesta fatia, ver CURATED_WEEKS_MAPPING.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Imprime o payload resultante sem publicar.')
        parser.add_argument('--slug', required=True, help='Slug do cliente (precisa estar em CURATED_WEEKS_MAPPING).')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        slug = options['slug']

        weeks = CURATED_WEEKS_MAPPING.get(slug)
        if weeks is None:
            raise CommandError(
                f'{slug!r} nao esta em CURATED_WEEKS_MAPPING ainda -- curadoria manual pendente '
                f'(so {sorted(CURATED_WEEKS_MAPPING)} tem mapeamento revisado hoje).'
            )

        program = get_active_program(slug=slug)
        if program is None:
            raise CommandError(f'{slug!r} nao tem PublicWorkoutProgram publicado ainda.')

        payload = dict(program)
        periodization = dict(payload.get('periodization') or {})
        periodization['weeks'] = weeks
        periodization.setdefault('volume_table', [])
        periodization.setdefault('note', '')
        payload['periodization'] = periodization

        errors = schema.validate_payload(payload)
        if errors:
            self.stdout.write(self.style.ERROR(f'{slug}: payload invalido, NAO publicado:'))
            for error in errors:
                self.stdout.write(f'  - {error}')
            return

        self.stdout.write(f'{slug}: periodization.weeks ->')
        for row in weeks:
            self.stdout.write(f"  S{row['week_number']}: {row['phase_type']}")

        if dry_run:
            self.stdout.write(self.style.WARNING(f'{slug}: --dry-run, nao publicado.'))
            return

        published = publish_program(slug=slug, payload=payload)
        self.stdout.write(self.style.SUCCESS(f'{slug}: publicado como v{published.version} (ativo).'))
