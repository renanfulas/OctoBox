"""
ARQUIVO: deixa as avaliacoes ja lancadas de um aluno no padrao da Franciele.

POR QUE ELE EXISTE:
- ate a migration 0045, sexo e altura so existiam no catalogo fixo (hoje
  Franciele e Rafael). Qualquer outro aluno avaliado por dobras cutaneas
  ficava com o relatorio pela metade: sem %gordura classificado, RCQ e IMC.
- em producao (15/10/2026) os casos reais sao giulia e willy, avaliados por
  7 dobras em 12/10 e inseridos direto no banco: sem sexo/altura, com a
  altura dentro das medidas (`altura_cm`) e com medidas por lado (`coxa_d`,
  `antebraco_e`...) que a tela mostra como chaves cruas.
- o padrao da Franciele: so as circunferencias unicas do sistema (lado D/E
  vira a media, com o detalhe por lado nas observacoes) + sexo/altura do
  aluno — o que da IMC, RCQ e %gordura classificados.

O QUE FAZ (por avaliacao, so o que falta):
1. grava sexo (--sex) e altura (--height, ou a `altura_cm` das medidas);
2. tira `altura_cm` das medidas e junta pares `<medida>_d`/`<medida>_e`:
   media na circunferencia unica (quando ela e do sistema e ainda nao
   existe) e o detalhe por lado nas observacoes;
3. com --recompute (+ --age), recalcula o %gordura das dobras gravadas nas
   observacoes com o sexo informado — so pra avaliacao que foi calculada
   pela formula masculina padrao de antes (aluna sem sexo cadastrado). As de
   giulia/willy NAO precisam: ja foram calculadas com a formula certa.
4. regera o comentario de IA (hero) quando a avaliacao mais recente mudou.

PONTOS CRITICOS:
- --dry-run mostra tudo o que mudaria, sem gravar nada. Rode antes.
- idempotente: rodar de novo nao muda mais nada.
- a idade nunca foi persistida: --recompute exige --age (idade na data da
  avaliacao); avaliacoes de anos diferentes, uma rodada por --date.

EXEMPLO (valores tirados das proprias observacoes da avaliacao):
  python manage.py complete_public_workout_assessment_profile giulia --sex F --height 160 --dry-run
  python manage.py complete_public_workout_assessment_profile willy --sex M --height 180 --dry-run
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from public_workouts.catalog import PUBLIC_WORKOUT_LIBRARY
from public_workouts.models import PublicWorkoutAssessment
from public_workouts.services import build_report, parse_skinfold_note, skinfold_body_fat

_SKINFOLD_SOURCES = ('skinfold_jp7', 'skinfold_jp3')
# Circunferencias unicas do sistema (mesmas flags do add_public_workout_assessment
# e rotulos de assessments-report.js). Fora daqui a tela mostra a chave crua.
_STANDARD_MEASUREMENTS = ('pescoco', 'cintura', 'abdomen', 'quadril', 'ombro', 'peito', 'braco', 'coxa', 'panturrilha')
_SIDE_SUFFIXES = {'_d': 'D', '_e': 'E'}
_SIDES_NOTE_PREFIX = 'Medidas por lado (D/E):'


def _fmt(value) -> str:
    return '—' if value is None else f'{float(value):g}'.replace('.', ',')


def normalize_measurements(measurements: dict) -> tuple[dict, str, float | None]:
    """(medidas no padrao, nota com o detalhe por lado, altura achada nas medidas)."""
    normalized = dict(measurements or {})
    height_cm = normalized.pop('altura_cm', None)

    sides: dict[str, dict[str, float]] = {}
    for key in list(normalized):
        base, suffix = key[:-2], key[-2:]
        if base and suffix in _SIDE_SUFFIXES:
            sides.setdefault(base, {})[suffix] = normalized.pop(key)

    details = []
    for base, pair in sorted(sides.items()):
        right, left = pair.get('_d'), pair.get('_e')
        values = [float(value) for value in (right, left) if value is not None]
        if base in _STANDARD_MEASUREMENTS and base not in normalized and values:
            normalized[base] = round(sum(values) / len(values), 2)
        details.append(f'{base} {_fmt(right)}/{_fmt(left)} cm')

    note = ''
    if details:
        note = (
            f'{_SIDES_NOTE_PREFIX} ' + '; '.join(details)
            + ' (usada a media nas circunferencias unicas do sistema).'
        )
    return normalized, note, float(height_cm) if height_cm is not None else None


class Command(BaseCommand):
    help = 'Deixa as avaliacoes de um aluno no padrao da Franciele (sexo/altura, medidas unicas, %gordura).'

    def add_arguments(self, parser):
        parser.add_argument('plan_slug', help='Slug do aluno (ex.: giulia)')
        parser.add_argument('--sex', dest='sex', choices=('F', 'M'), required=True, help='Sexo do aluno (F/M)')
        parser.add_argument(
            '--height', dest='height_cm', type=float, default=None,
            help='Altura em cm (IMC). Sem ela, usa a `altura_cm` gravada nas medidas, se houver',
        )
        parser.add_argument(
            '--recompute', dest='recompute', action='store_true',
            help='Recalcula o %%gordura das dobras com --sex (so se foi calculado pela formula masculina padrao)',
        )
        parser.add_argument('--age', dest='age', type=float, default=None, help='Idade na data da avaliacao (--recompute)')
        parser.add_argument('--date', dest='measured_at', default=None, help='So a avaliacao desta data (AAAA-MM-DD)')
        parser.add_argument('--dry-run', dest='dry_run', action='store_true', help='Mostra as mudancas sem gravar')

    def handle(self, *args, **options):
        plan_slug = options['plan_slug'].strip().lower()
        plan = PUBLIC_WORKOUT_LIBRARY.get(plan_slug)
        plan_sex = plan.assessment_sex if plan else None
        plan_height_cm = plan.height_cm if plan else None
        sex = options['sex']
        if plan_sex and plan_sex != sex:
            raise CommandError(f'--sex {sex} contradiz o catalogo de {plan_slug!r} ({plan_sex}).')
        height_cm = options['height_cm']
        if height_cm is not None and not 0 < height_cm < 300:
            raise CommandError(f'--height fora da faixa: {height_cm!r}')
        if options['recompute'] and options['age'] is None:
            raise CommandError('--recompute precisa de --age (idade na data da avaliacao).')

        queryset = PublicWorkoutAssessment.objects.filter(plan_slug=plan_slug).order_by('measured_at', 'pk')
        if options['measured_at']:
            try:
                queryset = queryset.filter(measured_at=date.fromisoformat(options['measured_at']))
            except ValueError as exc:
                raise CommandError(f'Data invalida: {options["measured_at"]!r} (use AAAA-MM-DD)') from exc
        assessments = list(queryset)
        if not assessments:
            raise CommandError(f'Nenhuma avaliacao de {plan_slug!r} pra completar.')

        # Tudo calculado (e validado) antes de gravar qualquer coisa.
        updates = []
        for assessment in assessments:
            fields = self._changes(
                assessment, sex=sex, height_cm=height_cm, recompute=options['recompute'], age=options['age'],
            )
            if fields:
                updates.append((assessment, fields))
        if not updates:
            self.stdout.write('Nada a mudar: as avaliacoes ja estao no padrao.')
            return

        for assessment, fields in updates:
            self.stdout.write(self._describe(assessment, fields))
            if (
                not options['recompute'] and sex == 'F' and not plan_sex and not assessment.sex
                and assessment.body_fat_source in _SKINFOLD_SOURCES
            ):
                self.stdout.write(
                    '    confira o %gordura: se foi calculado pela formula masculina (padrao antigo sem sexo), '
                    'rode de novo com --recompute --age <idade>.'
                )
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('--dry-run: nada foi gravado.'))
            return

        with transaction.atomic():
            for assessment, fields in updates:
                for name, value in fields.items():
                    setattr(assessment, name, value)
                assessment.save(update_fields=list(fields))

        latest = PublicWorkoutAssessment.objects.filter(plan_slug=plan_slug).order_by('measured_at', 'pk').last()
        resolved_sex = plan_sex or sex
        resolved_height = plan_height_cm or (float(latest.height_cm) if latest.height_cm is not None else None)
        if any(assessment.pk == latest.pk for assessment, _ in updates):
            from public_workouts.assessment_hero_ai import generate_and_store_hero_commentary

            hero_text = generate_and_store_hero_commentary(
                plan_slug=plan_slug, sex=resolved_sex, height_cm=resolved_height
            )
            self.stdout.write(f'  Comentario (hero): {hero_text or "nao gerado (sem ANTHROPIC_API_KEY, timeout ou erro)."}')

        indicators = build_report(plan_slug=plan_slug, sex=resolved_sex, height_cm=resolved_height)['indicators'] or {}
        self.stdout.write(self.style.SUCCESS(f'{len(updates)} avaliacao(oes) de {plan_slug} atualizada(s).'))
        for key, label in (('bmi', 'IMC'), ('whr', 'RCQ'), ('body_fat_percent', '%Gordura')):
            if indicators.get(key):
                self.stdout.write(f'  {label}: {indicators[key]["value"]} ({indicators[key]["classification"]["label"]})')

    def _changes(self, assessment, *, sex, height_cm, recompute, age) -> dict:
        fields = {}
        if not assessment.sex:
            fields['sex'] = sex

        normalized, sides_note, measured_height = normalize_measurements(assessment.measurements)
        if normalized != (assessment.measurements or {}):
            fields['measurements'] = normalized
        if sides_note and _SIDES_NOTE_PREFIX not in (assessment.notes or ''):
            fields['notes'] = f'{assessment.notes} {sides_note}'.strip()

        if height_cm is not None and measured_height is not None and abs(height_cm - measured_height) > 0.5:
            raise CommandError(
                f'{assessment.measured_at}: --height {height_cm:g} contradiz a altura_cm gravada ({measured_height:g}).'
            )
        height = height_cm if height_cm is not None else measured_height
        if height is not None and assessment.height_cm is None:
            fields['height_cm'] = Decimal(str(height))

        if recompute and assessment.body_fat_source in _SKINFOLD_SOURCES:
            skinfolds = parse_skinfold_note(assessment.notes)
            body_fat, source = skinfold_body_fat(sex=sex, age=age, skinfolds=skinfolds)
            if body_fat is None:
                raise CommandError(
                    f'{assessment.measured_at}: nao deu pra recalcular com as dobras gravadas ({skinfolds or "nenhuma"}).'
                )
            new_value = Decimal(str(round(body_fat, 1)))
            if new_value != assessment.body_fat_percent or source != assessment.body_fat_source:
                fields['body_fat_percent'] = new_value
                fields['body_fat_source'] = source
        return fields

    def _describe(self, assessment, fields) -> str:
        parts = []
        if 'sex' in fields:
            parts.append(f'sexo {fields["sex"]}')
        if 'height_cm' in fields:
            parts.append(f'altura {_fmt(fields["height_cm"])} cm')
        if 'measurements' in fields:
            removed = sorted(set(assessment.measurements or {}) - set(fields['measurements']))
            parts.append(f'medidas sem {", ".join(removed)}' if removed else 'medidas ajustadas')
        if 'notes' in fields:
            parts.append('detalhe D/E nas observacoes')
        if 'body_fat_percent' in fields:
            parts.append(
                f'%gordura {assessment.body_fat_percent} -> {fields["body_fat_percent"]} ({fields["body_fat_source"]})'
            )
        return f'  {assessment.measured_at}: ' + ', '.join(parts)
