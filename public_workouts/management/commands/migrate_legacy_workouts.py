"""
COMANDO: migrate_legacy_workouts

POR QUE EXISTE:
- Onda A2 do CORDA (docs/plans/public-workouts-produtizacao-corda.md) —
  publica os 10 programas de consultoria reais (hoje só existem como HTML
  legado em templates/public_workouts/<slug>.html) como `PublicWorkoutProgram`
  de verdade, usando o parser determinístico de `public_workouts/parser.py`
  (ver docstring lá: por que isso não precisa de LLM).

USO:
    python manage.py migrate_legacy_workouts --dry-run                # todos os 10, so imprime
    python manage.py migrate_legacy_workouts --dry-run --slug=bruno   # 1 so, pra revisar
    python manage.py migrate_legacy_workouts --slug=bruno             # publica de verdade

PONTOS CRITICOS:
- Fluxo de revisao (Onda A2, item 3 do "O que fazer"): rode 1 slug com
  --dry-run, compare visualmente contra o HTML original, ajuste o parser
  se achar erro, repita. So publique quando o dry-run bater.
- Metadados de negocio (program_id/program_label/started_on/weeks) NAO vem
  do HTML -- e decisao sua, nao dado extraivel (ver LEGACY_PROGRAM_METADATA
  abaixo). `accent_variant` e a UNICA excecao: ja existe em
  PUBLIC_WORKOUT_LIBRARY[slug].assessment_sex (schema.py copia esse mesmo
  vocabulario), entao e derivado automaticamente, nunca hardcoded aqui.
- `weeks` tem um candidato AUTO-SUGERIDO (maior "Semana N" encontrado no
  proprio HTML) so pra sua conferencia no dry-run -- nunca e o valor final
  calado; o valor que de fato publica vem de LEGACY_PROGRAM_METADATA.
- Nunca publica payload invalido: valida contra schema.py antes de chamar
  publish_program (que ja validaria de qualquer forma, mas o erro aqui sai
  mais legivel, com o path exato do campo que falhou).
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from public_workouts import schema
from public_workouts.management.commands.extract_movements_from_html import LEGACY_WORKOUT_SLUGS
from public_workouts.parser import build_program_payload_from_html
from public_workouts.services import publish_program

_WEEK_NUMBER_RE = re.compile(r'[Ss]emana\s+(\d+)')

# Decisao de negocio, nao dado extraivel do HTML -- ver docstring do modulo.
# `started_on`: data real (ISO YYYY-MM-DD) em que o aluno comecou o
# mesociclo atual. Preenchido em 2026-09-15 a partir da data do commit no
# GitHub em que o HTML de cada aluno foi colocado/reescrito de verdade
# (pedido explicito do Renan: "a data que esta la foi a data que comecou"),
# ignorando commits cosmeticos que tocaram os 10 de uma vez sem mudar
# conteudo de treino (extracao de design system, aba Avaliacoes):
#   bruno/giovanna/john/milene: ja existiam no 1o commit do repo
#     (32339c6, 2026-06-23) -- nenhuma reescrita de conteudo depois disso,
#     entao 2026-06-23 e' a data mais antiga visivel no historico.
#   henrique: e7853bd (2026-08-26, PR #162 "novo treino publico ... 5 dias").
#   johnespanha: 852a351 (2026-08-28, PR #170 "novo treino publico ...").
#   juliana: 703564a (2026-08-31, "novo ciclo Juliana -- quadriceps alta
#     frequencia 4 dias") -- reescrita mais recente que o PR #158 (02/08).
#   franciele: 2bf74fe (2026-09-06, "adiciona treino publico da Franciele").
#   rafael: 93ac1fe (2026-09-06, "adiciona treino publico do Rafael").
#   thaislima: mesma situacao de bruno/giovanna/john/milene (2026-06-23).
# Pedido explicito do Renan pra quem ja passou da duracao (`weeks`) hoje
# (bruno/giovanna/john/milene/thaislima, todos com data de 2026-06-23):
# usar hoje-14 dias (2026-09-01) em vez da data real do commit, pra nao
# publicar um mesociclo "encerrado ha meses" -- ver
# docs/plans/public-workouts-produtizacao-corda.md pra contexto da decisao.
LEGACY_PROGRAM_METADATA: dict[str, dict[str, object]] = {
    # `weeks` dos 8 slugs com periodization abaixo foi realinhado com o
    # numero de linhas de `periodization.weeks_table` (payload real,
    # extraido pelo parser) apos a fatia Cardio+Periodizacao do PR #249 --
    # o valor antigo era anterior a essa fatia e ficava atras do que a
    # propria tabela de periodizacao mostra (ex.: bruno tinha weeks=5 com
    # tabela de 6 semanas). johnespanha/thaislima nao tem periodization
    # nesta fatia, entao ficam como estavam.
    'bruno': {'program_label': 'Treino Bruno', 'weeks': 6, 'started_on': '2026-09-01'},
    'franciele': {'program_label': 'Treino Franciele', 'weeks': 5, 'started_on': '2026-09-06'},
    'giovanna': {'program_label': 'Treino Giovanna', 'weeks': 6, 'started_on': '2026-09-01'},
    'henrique': {'program_label': 'Treino Henrique', 'weeks': 6, 'started_on': '2026-08-26'},
    'john': {'program_label': 'Treino John Espanha (Legado)', 'weeks': 6, 'started_on': '2026-09-01'},
    'johnespanha': {'program_label': 'Treino John Espanha', 'weeks': 4, 'started_on': '2026-08-28'},
    'juliana': {'program_label': 'Treino Juliana', 'weeks': 6, 'started_on': '2026-08-31'},
    'milene': {'program_label': 'Treino Milene', 'weeks': 6, 'started_on': '2026-09-01'},
    'rafael': {'program_label': 'Treino Rafael', 'weeks': 7, 'started_on': '2026-09-06'},
    'thaislima': {'program_label': 'Treino Thais Lima', 'weeks': 4, 'started_on': '2026-09-01'},
}


class Command(BaseCommand):
    help = (
        'Migra os 10 programas legados de /renan/<slug> pra PublicWorkoutProgram, '
        'via parser deterministico (nao usa LLM -- ver public_workouts/parser.py).'
    )

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Imprime o payload extraido sem publicar.')
        parser.add_argument('--slug', help='Migra so este slug (default: todos os 10).')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        only_slug = options.get('slug')

        slugs = (only_slug,) if only_slug else LEGACY_WORKOUT_SLUGS
        if only_slug and only_slug not in LEGACY_WORKOUT_SLUGS:
            raise CommandError(f'Slug desconhecido: {only_slug!r}. Esperado um de {LEGACY_WORKOUT_SLUGS}')

        from student_app.views.public_workout_views import PUBLIC_WORKOUT_LIBRARY

        template_dir = Path(settings.BASE_DIR) / 'templates' / 'public_workouts'

        for slug in slugs:
            path = template_dir / f'{slug}.html'
            if not path.exists():
                self.stdout.write(self.style.WARNING(f'Template ausente, pulando: {path}'))
                continue

            html = path.read_text(encoding='utf-8')
            metadata = LEGACY_PROGRAM_METADATA[slug]
            plan = PUBLIC_WORKOUT_LIBRARY.get(slug)
            accent_variant = plan.assessment_sex if plan else None

            suggested_weeks = self._suggest_weeks(html)
            configured_weeks = metadata['weeks']
            configured_started_on = metadata.get('started_on')
            started_on = configured_started_on or date.today().isoformat()

            payload, skipped = build_program_payload_from_html(
                html=html,
                program_id=f'{slug}-legado-v1',
                program_label=metadata['program_label'],
                started_on=started_on,
                weeks=configured_weeks,
                accent_variant=accent_variant,
            )

            errors = schema.validate_payload(payload)

            self._print_report(
                slug=slug, payload=payload, skipped=skipped, errors=errors,
                suggested_weeks=suggested_weeks, configured_weeks=configured_weeks,
                configured_started_on=configured_started_on,
            )

            if errors:
                self.stdout.write(self.style.ERROR(f'{slug}: payload invalido, NAO publicado.'))
                continue

            if dry_run:
                continue

            program = publish_program(slug=slug, payload=payload)
            self.stdout.write(self.style.SUCCESS(f'{slug}: publicado como v{program.version} (ativo).'))

    def _suggest_weeks(self, html: str) -> int | None:
        numbers = [int(match) for match in _WEEK_NUMBER_RE.findall(html)]
        return max(numbers) if numbers else None

    def _print_report(
        self, *, slug, payload, skipped, errors, suggested_weeks, configured_weeks, configured_started_on,
    ) -> None:
        accent = payload['accent_variant'] or 'neutro'
        self.stdout.write(
            f"\n=== {slug} ({payload['program_id']}, {payload['weeks']} semanas, "
            f"started_on={payload['started_on']}, accent={accent}) ==="
        )
        if suggested_weeks is not None and suggested_weeks != configured_weeks:
            self.stdout.write(self.style.WARNING(
                f'  aviso: HTML sugere {suggested_weeks} semanas (maior "Semana N" encontrado), '
                f'configurado {configured_weeks} -- confira LEGACY_PROGRAM_METADATA.'
            ))
        if configured_started_on is None:
            self.stdout.write(self.style.WARNING(
                f"  aviso: started_on nao configurado para {slug!r}, usando hoje "
                f"({payload['started_on']}) -- preencha LEGACY_PROGRAM_METADATA['{slug}']['started_on'] "
                f"quando souber a data real em que o mesociclo comecou."
            ))

        total_movements = 0
        for day in payload['days']:
            self.stdout.write(f"[{day['day_id']}] {day['label']}")
            for block in day['blocks']:
                for movement in block['movements']:
                    total_movements += 1
                    tracked = 'Y' if movement['is_tracked'] else 'N'
                    self.stdout.write(
                        f"  {movement['movement_slug']:<40} "
                        f"reps=\"{movement['reps_spec']}\" rir=\"{movement['rir_spec']}\" tracked={tracked}"
                    )

        for skip in skipped:
            self.stdout.write(f'  [SKIPPED] [{skip.day_id}] {skip.name} — {skip.reason}')

        self.stdout.write(
            f'{len(payload["days"])} dias, {total_movements} movimentos extraidos, {len(skipped)} pulados.'
        )
        if errors:
            for error in errors:
                self.stdout.write(self.style.ERROR(f'  ERRO DE SCHEMA: {error}'))
