"""
COMANDO: extract_movements_from_html

POR QUE EXISTE:
- Onda A0 do CORDA (docs/plans/public-workouts-produtizacao-corda.md) — os
  10 programas legados de `/renan/<slug>` tem "Ver no MuscleWiki" em cada
  exercicio, mas esse link so existe hoje espalhado nos 10 HTMLs. Este
  comando varre os templates, extrai (nome, url) por `<a class="wiki-btn">`
  e semeia PublicWorkoutMovement — o catalogo PROPRIO do corredor (V1/D.00:
  nunca escreve em `student_app.MovementLibrary`, a tabela por box).
- Tambem semeia os movimentos "essenciais" de CrossFit a partir de uma
  copia READ-ONLY da lista de `seed_movement_library` (modality=CROSSFIT,
  status=ACTIVE — ja curada, nao precisa de revisao).

USO:
    python manage.py extract_movements_from_html
    python manage.py extract_movements_from_html --dry-run

PONTOS CRITICOS:
- `movement_pattern` fica em branco de proposito (ver docstring de
  public_workouts/models.py) — nao e advinhado por este comando.
- Idempotente via update_or_create por slug. Rodar de novo NAO sobrescreve
  `movement_pattern` nem `status` de um movimento ja revisado manualmente
  (so toca label_pt/label_en/reference_url/modality na re-extracao).
- Parser usa html.parser.HTMLParser (stdlib) escopado por bloco `<div
  class="ex">...</div>` — uma abordagem por regex "ex-name mais proximo
  wiki-btn" cruza a fronteira de blocos sem wiki-btn (ex.: os blocos de
  corrida/cardio, que nao tem link) e associa o nome errado ao link do
  PROXIMO exercicio. Achado ao prototipar este comando, antes de commitar.
"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from public_workouts.models import PublicWorkoutMovement, PublicWorkoutMovementModality, PublicWorkoutMovementStatus
from public_workouts.musclewiki import movement_slug_from_url


# Os 10 programas migrados na Onda A2 (docs/plans/public-workouts-produtizacao-corda.md).
# `_base.html` e `offline.html` nao sao programas, e os `archive-*.html` sao
# versoes descontinuadas — nenhum dos dois entra na extracao.
LEGACY_WORKOUT_SLUGS: tuple[str, ...] = (
    'bruno',
    'franciele',
    'giovanna',
    'henrique',
    'john',
    'johnespanha',
    'juliana',
    'milene',
    'rafael',
    'thaislima',
)

# Copia READ-ONLY da lista de essenciais de CrossFit — fonte de verdade
# continua sendo student_app/management/commands/seed_movement_library.py.
# Copiado (nao importado) de proposito: D.00 classifica "copiar padrao"
# como acoplamento zero, e importar de dentro de outro app criaria uma
# dependencia desnecessaria entre um comando SHARED e um comando TENANT.
CROSSFIT_ESSENTIALS: tuple[dict[str, str], ...] = (
    {'slug': 'clean', 'label_pt': 'Clean', 'label_en': 'Clean', 'reference_url': 'https://www.crossfit.com/essentials/the-clean'},
    {'slug': 'clean-and-jerk', 'label_pt': 'Clean and Jerk', 'label_en': 'Clean and Jerk', 'reference_url': 'https://www.crossfit.com/essentials/the-clean-and-jerk'},
    {'slug': 'snatch', 'label_pt': 'Snatch', 'label_en': 'Snatch', 'reference_url': 'https://www.crossfit.com/essentials/the-snatch'},
    {'slug': 'power-clean', 'label_pt': 'Power Clean', 'label_en': 'Power Clean', 'reference_url': 'https://www.crossfit.com/essentials/the-power-clean'},
    {'slug': 'power-snatch', 'label_pt': 'Power Snatch', 'label_en': 'Power Snatch', 'reference_url': ''},
    {'slug': 'hang-clean', 'label_pt': 'Hang Clean', 'label_en': 'Hang Clean', 'reference_url': ''},
    {'slug': 'hang-power-clean', 'label_pt': 'Hang Power Clean', 'label_en': 'Hang Power Clean', 'reference_url': ''},
    {'slug': 'hang-snatch', 'label_pt': 'Hang Snatch', 'label_en': 'Hang Snatch', 'reference_url': ''},
    {'slug': 'overhead-press', 'label_pt': 'Overhead Press', 'label_en': 'Overhead Press (Strict Press)', 'reference_url': 'https://www.crossfit.com/essentials/the-press'},
    {'slug': 'push-press', 'label_pt': 'Push Press', 'label_en': 'Push Press', 'reference_url': 'https://www.crossfit.com/essentials/the-push-press'},
    {'slug': 'push-jerk', 'label_pt': 'Push Jerk', 'label_en': 'Push Jerk', 'reference_url': 'https://www.crossfit.com/essentials/the-push-jerk'},
    {'slug': 'split-jerk', 'label_pt': 'Split Jerk', 'label_en': 'Split Jerk', 'reference_url': ''},
    {'slug': 'thruster', 'label_pt': 'Thruster', 'label_en': 'Thruster', 'reference_url': 'https://www.crossfit.com/essentials/the-thruster'},
    {'slug': 'back-squat', 'label_pt': 'Agachamento Costas', 'label_en': 'Back Squat', 'reference_url': 'https://www.crossfit.com/essentials/the-back-squat'},
    {'slug': 'front-squat', 'label_pt': 'Agachamento Frontal', 'label_en': 'Front Squat', 'reference_url': 'https://www.crossfit.com/essentials/the-front-squat'},
    {'slug': 'overhead-squat', 'label_pt': 'Agachamento Overhead', 'label_en': 'Overhead Squat', 'reference_url': 'https://www.crossfit.com/essentials/the-overhead-squat'},
    {'slug': 'air-squat', 'label_pt': 'Agachamento Livre', 'label_en': 'Air Squat', 'reference_url': 'https://www.crossfit.com/essentials/the-air-squat'},
    {'slug': 'wall-ball', 'label_pt': 'Wall Ball', 'label_en': 'Wall Ball Shot', 'reference_url': 'https://www.crossfit.com/essentials/the-wall-ball-shot'},
    {'slug': 'deadlift', 'label_pt': 'Levantamento Terra', 'label_en': 'Deadlift', 'reference_url': 'https://www.crossfit.com/essentials/the-deadlift'},
    {'slug': 'sumo-deadlift-high-pull', 'label_pt': 'Sumo Deadlift High Pull', 'label_en': 'Sumo Deadlift High Pull', 'reference_url': 'https://www.crossfit.com/essentials/the-sumo-deadlift-high-pull'},
    {'slug': 'pull-up', 'label_pt': 'Barra Fixa', 'label_en': 'Pull-up', 'reference_url': 'https://www.crossfit.com/essentials/the-pull-up'},
    {'slug': 'chest-to-bar', 'label_pt': 'Chest-to-Bar', 'label_en': 'Chest-to-Bar Pull-up', 'reference_url': ''},
    {'slug': 'muscle-up', 'label_pt': 'Muscle-up', 'label_en': 'Muscle-up (Bar)', 'reference_url': 'https://www.crossfit.com/essentials/the-muscle-up'},
    {'slug': 'ring-muscle-up', 'label_pt': 'Muscle-up nas Argolas', 'label_en': 'Ring Muscle-up', 'reference_url': ''},
    {'slug': 'toes-to-bar', 'label_pt': 'Toes-to-Bar', 'label_en': 'Toes-to-Bar', 'reference_url': 'https://www.crossfit.com/essentials/toes-to-bar'},
    {'slug': 'ring-row', 'label_pt': 'Ring Row', 'label_en': 'Ring Row', 'reference_url': ''},
    {'slug': 'push-up', 'label_pt': 'Flexao de Bracos', 'label_en': 'Push-up', 'reference_url': 'https://www.crossfit.com/essentials/the-push-up'},
    {'slug': 'handstand-push-up', 'label_pt': 'Flexao Invertida (HSPU)', 'label_en': 'Handstand Push-up', 'reference_url': 'https://www.crossfit.com/essentials/the-handstand-push-up'},
    {'slug': 'handstand-walk', 'label_pt': 'Caminhada Invertida', 'label_en': 'Handstand Walk', 'reference_url': ''},
    {'slug': 'dip', 'label_pt': 'Mergulho (Dip)', 'label_en': 'Ring Dip', 'reference_url': 'https://www.crossfit.com/essentials/the-ring-dip'},
    {'slug': 'box-jump', 'label_pt': 'Salto na Caixa', 'label_en': 'Box Jump', 'reference_url': 'https://www.crossfit.com/essentials/the-box-jump'},
    {'slug': 'double-under', 'label_pt': 'Double Under', 'label_en': 'Double Under', 'reference_url': 'https://www.crossfit.com/essentials/the-double-under'},
    {'slug': 'single-under', 'label_pt': 'Single Under', 'label_en': 'Single Under', 'reference_url': ''},
    {'slug': 'burpee', 'label_pt': 'Burpee', 'label_en': 'Burpee', 'reference_url': 'https://www.crossfit.com/essentials/the-burpee'},
    {'slug': 'box-step-up', 'label_pt': 'Step-up na Caixa', 'label_en': 'Box Step-up', 'reference_url': ''},
    {'slug': 'row', 'label_pt': 'Remo (Rower)', 'label_en': 'Row (Rower)', 'reference_url': ''},
    {'slug': 'assault-bike', 'label_pt': 'Bike (Assault)', 'label_en': 'Assault Bike', 'reference_url': ''},
    {'slug': 'ski-erg', 'label_pt': 'Ski Erg', 'label_en': 'Ski Erg', 'reference_url': ''},
    {'slug': 'run', 'label_pt': 'Corrida', 'label_en': 'Run', 'reference_url': ''},
    {'slug': 'kettlebell-swing', 'label_pt': 'Kettlebell Swing', 'label_en': 'Kettlebell Swing', 'reference_url': 'https://www.crossfit.com/essentials/the-kettlebell-swing'},
    {'slug': 'turkish-get-up', 'label_pt': 'Turkish Get-up', 'label_en': 'Turkish Get-up', 'reference_url': ''},
    {'slug': 'ghd-sit-up', 'label_pt': 'GHD Sit-up', 'label_en': 'GHD Sit-up', 'reference_url': 'https://www.crossfit.com/essentials/the-ghd-sit-up'},
    {'slug': 'sit-up', 'label_pt': 'Abdominal', 'label_en': 'Sit-up', 'reference_url': ''},
    {'slug': 'back-extension', 'label_pt': 'Extensao de Lombar', 'label_en': 'Back Extension (GHD)', 'reference_url': 'https://www.crossfit.com/essentials/the-back-extension'},
    {'slug': 'plank', 'label_pt': 'Prancha', 'label_en': 'Plank', 'reference_url': ''},
)


class _ExerciseBlockParser(HTMLParser):
    """Extrai (nome, url) de cada bloco `<div class="ex">...</div>`.

    Escopado por bloco de proposito: um bloco sem `wiki-btn` (ex.: os
    inserts de corrida/cardio entre exercicios) simplesmente nao produz
    par nenhum, em vez de "vazar" e pegar o wiki-btn do proximo bloco.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.pairs: list[tuple[str, str]] = []
        self._depth = 0  # profundidade de divs dentro do bloco .ex atual (None = fora)
        self._in_block = False
        self._in_name = False
        self._name_parts: list[str] = []
        self._current_url: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == 'div':
            css_class = attrs_dict.get('class', '') or ''
            classes = css_class.split()
            if not self._in_block and classes == ['ex']:
                self._in_block = True
                self._depth = 1
                self._name_parts = []
                self._current_url = None
                return
            if self._in_block:
                self._depth += 1
                if 'ex-name' in classes:
                    self._in_name = True
                    self._name_parts = []
        elif tag == 'a' and self._in_block and self._current_url is None:
            css_class = (attrs_dict.get('class') or '').split()
            if 'wiki-btn' in css_class and attrs_dict.get('href'):
                self._current_url = attrs_dict['href']

    def handle_endtag(self, tag: str) -> None:
        if tag == 'div' and self._in_block:
            if self._in_name:
                self._in_name = False
            self._depth -= 1
            if self._depth == 0:
                name = ''.join(self._name_parts).strip()
                if name and self._current_url:
                    self.pairs.append((name, self._current_url))
                self._in_block = False

    def handle_data(self, data: str) -> None:
        if self._in_name:
            self._name_parts.append(data)


def _extract_pairs_from_html(html: str) -> list[tuple[str, str]]:
    parser = _ExerciseBlockParser()
    parser.feed(html)
    return parser.pairs


class Command(BaseCommand):
    help = (
        'Extrai (nome, url MuscleWiki) dos 10 programas legados de /renan/ e semeia '
        'PublicWorkoutMovement — nunca escreve em student_app.MovementLibrary (idempotente).'
    )

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Imprime sem salvar no banco.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        html_movements = self._extract_html_movements()
        self.stdout.write(f'Extraidos {len(html_movements)} movimentos unicos de {len(LEGACY_WORKOUT_SLUGS)} programas.')

        if dry_run:
            for movement in html_movements:
                self.stdout.write(f"  [strength/pending] {movement['slug']} — {movement['label_pt']}")
            for movement in CROSSFIT_ESSENTIALS:
                self.stdout.write(f"  [crossfit/active]  {movement['slug']} — {movement['label_pt']}")
            self.stdout.write(self.style.WARNING(
                f'\nDRY RUN — {len(html_movements) + len(CROSSFIT_ESSENTIALS)} movimentos listados, nenhum salvo.'
            ))
            return

        html_slugs = {m['slug'] for m in html_movements}
        crossfit_slugs = {m['slug'] for m in CROSSFIT_ESSENTIALS}
        overlap = html_slugs & crossfit_slugs
        if overlap:
            self.stdout.write(self.style.WARNING(
                f'{len(overlap)} slug(s) extraido(s) do HTML tambem estao nos essenciais de '
                f'CrossFit — a versao CrossFit (curada) vence: {sorted(overlap)}'
            ))

        created, updated = 0, 0
        with transaction.atomic():
            for movement in html_movements:
                c, u = self._upsert(
                    slug=movement['slug'],
                    label_pt=movement['label_pt'],
                    reference_url=movement['reference_url'],
                    modality=PublicWorkoutMovementModality.STRENGTH,
                    default_status=PublicWorkoutMovementStatus.PENDING,
                )
                created += c
                updated += u
            for movement in CROSSFIT_ESSENTIALS:
                c, u = self._upsert(
                    slug=movement['slug'],
                    label_pt=movement['label_pt'],
                    label_en=movement['label_en'],
                    reference_url=movement['reference_url'],
                    modality=PublicWorkoutMovementModality.CROSSFIT,
                    default_status=PublicWorkoutMovementStatus.ACTIVE,
                )
                created += c
                updated += u

        self.stdout.write(self.style.SUCCESS(f'PublicWorkoutMovement: {created} criados, {updated} atualizados.'))

    def _extract_html_movements(self) -> list[dict[str, str]]:
        by_slug: dict[str, dict[str, object]] = {}
        template_dir = Path(settings.BASE_DIR) / 'templates' / 'public_workouts'

        for workout_slug in LEGACY_WORKOUT_SLUGS:
            path = template_dir / f'{workout_slug}.html'
            if not path.exists():
                self.stdout.write(self.style.WARNING(f'Template ausente, pulando: {path}'))
                continue
            html = path.read_text(encoding='utf-8')
            for name, url in _extract_pairs_from_html(html):
                movement_slug = movement_slug_from_url(url)
                if not movement_slug:
                    continue
                entry = by_slug.setdefault(movement_slug, {'names': {}, 'urls': {}})
                entry['names'][name] = entry['names'].get(name, 0) + 1
                entry['urls'][url] = entry['urls'].get(url, 0) + 1

        result = []
        for movement_slug in sorted(by_slug):
            entry = by_slug[movement_slug]
            # canonico = mais frequente entre os 10 programas; empate = mais curto (mais limpo pro catalogo).
            canonical_name = sorted(entry['names'].items(), key=lambda kv: (-kv[1], len(kv[0])))[0][0]
            canonical_url = sorted(entry['urls'].items(), key=lambda kv: (-kv[1], len(kv[0])))[0][0]
            result.append({'slug': movement_slug, 'label_pt': canonical_name, 'reference_url': canonical_url})
        return result

    def _upsert(
        self,
        *,
        slug: str,
        label_pt: str,
        reference_url: str,
        modality: str,
        default_status: str,
        label_en: str = '',
    ) -> tuple[int, int]:
        existing = PublicWorkoutMovement.objects.filter(slug=slug).first()
        if existing is None:
            PublicWorkoutMovement.objects.create(
                slug=slug,
                label_pt=label_pt,
                label_en=label_en,
                reference_url=reference_url,
                modality=modality,
                status=default_status,
            )
            return 1, 0

        # Re-extracao: atualiza so o que o HTML/lista essencial realmente descreve.
        # NUNCA sobrescreve movement_pattern nem status — podem ter sido
        # revisados manualmente depois do ultimo seed.
        existing.label_pt = label_pt
        if label_en:
            existing.label_en = label_en
        existing.reference_url = reference_url
        existing.modality = modality
        existing.save(update_fields=['label_pt', 'label_en', 'reference_url', 'modality', 'updated_at'])
        return 0, 1
