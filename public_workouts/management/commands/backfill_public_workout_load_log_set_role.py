"""
COMANDO: backfill_public_workout_load_log_set_role

POR QUE EXISTE:
- Plano docs/plans/curva-grafico-hierarquia-e-set-role.md (Revisão 8),
  §7.3/§7.12 — a Migration A adiciona `set_role` NULLABLE em
  `PublicWorkoutLoadLog`; este comando preenche o histórico existente
  (anterior ao campo) com `legacy_unknown`, nunca `top_set` — assumir
  `top_set` fabricaria precisão sobre dado que nunca teve essa
  classificação. `legacy_unknown` nunca entra em elegibilidade de
  curva/tendência/recorde (ver `progress_eligibility.py`), mas continua
  visível como histórico anterior.

USO:
    python manage.py backfill_public_workout_load_log_set_role --dry-run
    python manage.py backfill_public_workout_load_log_set_role

PONTOS CRÍTICOS:
- Idempotente: só toca linhas com `set_role__isnull=True`. Rodar de novo
  depois do PR 1 (escritor já compatível, nunca mais grava NULL) só
  confirma zero linha residual — não reclassifica nada que já tenha um
  valor real.
- Roda uma vez manualmente entre a Migration A e a Migration B/checkpoint
  de produção (§7.12) — não é acionado automaticamente por nenhum
  deploy/signal.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from public_workouts.models import PublicWorkoutLoadLog
from public_workouts.models import PublicWorkoutLoadLogSetRole as SetRole


class Command(BaseCommand):
    help = (
        'Preenche PublicWorkoutLoadLog.set_role=legacy_unknown pra todo registro '
        'anterior ao campo (set_role NULL). Idempotente.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true', help='So conta quantas linhas seriam afetadas, nao escreve nada.'
        )

    def handle(self, *args, **options):
        queryset = PublicWorkoutLoadLog.objects.filter(set_role__isnull=True)
        count = queryset.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS('Nenhuma linha com set_role NULL -- nada a fazer.'))
            return

        if options['dry_run']:
            self.stdout.write(self.style.WARNING(f'{count} linha(s) receberiam set_role=legacy_unknown (--dry-run, nada escrito).'))
            return

        updated = queryset.update(set_role=SetRole.LEGACY_UNKNOWN)
        self.stdout.write(self.style.SUCCESS(f'{updated} linha(s) marcadas como set_role=legacy_unknown.'))
