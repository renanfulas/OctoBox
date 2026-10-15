"""
ARQUIVO: completa sexo e altura nas avaliacoes ja lancadas de um aluno.

POR QUE ELE EXISTE:
- ate a migration 0045, sexo e altura so existiam no catalogo fixo (hoje
  Franciele e Rafael). Qualquer outro aluno avaliado por dobras cutaneas
  ficava com o relatorio pela metade (sem %gordura classificado, RCQ e IMC)
  — e, se fosse mulher, com o %gordura calculado pela formula MASCULINA,
  padrao silencioso que o comando presencial e a autoavaliacao usavam.
- este comando grava sexo/altura nas avaliacoes do aluno e, onde a formula
  errada foi usada, recalcula o %gordura a partir das dobras que ficaram no
  texto da avaliacao ("Dobras (mm): ...").

PONTOS CRITICOS:
- so recalcula avaliacoes por dobra (skinfold_jp7/jp3) calculadas SEM sexo
  conhecido (nada gravado e nada no catalogo) quando o sexo informado e F —
  com M, a formula usada por padrao ja era a certa.
- recalcular precisa da idade, que nunca foi persistida: --age e obrigatorio
  nesse caso. Avaliacoes de anos diferentes: rode uma vez por --date, cada
  uma com a idade daquela data.
- --dry-run mostra tudo o que mudaria, sem gravar nada.
- regera o comentario de IA (hero) da avaliacao mais recente quando ela
  mudou — o texto antigo podia citar um %gordura errado.

EXEMPLO:
  python manage.py complete_public_workout_assessment_profile <slug> \\
      --sex F --height 165 --age 31 --dry-run
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from public_workouts.catalog import PUBLIC_WORKOUT_LIBRARY
from public_workouts.formulas import Sex
from public_workouts.models import PublicWorkoutAssessment
from public_workouts.services import build_report, parse_skinfold_note, skinfold_body_fat

_SKINFOLD_SOURCES = ('skinfold_jp7', 'skinfold_jp3')


class Command(BaseCommand):
    help = 'Grava sexo/altura nas avaliacoes de um aluno e corrige %gordura de dobras calculado sem o sexo.'

    def add_arguments(self, parser):
        parser.add_argument('plan_slug', help='Slug do plano em PUBLIC_WORKOUT_LIBRARY')
        parser.add_argument('--sex', dest='sex', choices=('F', 'M'), required=True, help='Sexo do aluno (F/M)')
        parser.add_argument('--height', dest='height_cm', type=float, default=None, help='Altura em cm (IMC)')
        parser.add_argument(
            '--age', dest='age', type=float, default=None,
            help='Idade na data da avaliacao — obrigatoria quando ha %%gordura de dobras a recalcular',
        )
        parser.add_argument('--date', dest='measured_at', default=None, help='So a avaliacao desta data (AAAA-MM-DD)')
        parser.add_argument('--dry-run', dest='dry_run', action='store_true', help='Mostra as mudancas sem gravar')

    def handle(self, *args, **options):
        plan_slug = options['plan_slug'].strip().lower()
        plan = PUBLIC_WORKOUT_LIBRARY.get(plan_slug)
        if plan is None:
            raise CommandError(f'Plano publico desconhecido: {plan_slug!r}')
        sex = options['sex']
        if plan.assessment_sex and plan.assessment_sex != sex:
            raise CommandError(f'--sex {sex} contradiz o catalogo de {plan_slug!r} ({plan.assessment_sex}).')
        height_cm = options['height_cm']
        if height_cm is not None and not 0 < height_cm < 300:
            raise CommandError(f'--height fora da faixa: {height_cm!r}')

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
            fields = self._changes(assessment, plan=plan, sex=sex, height_cm=height_cm, age=options['age'])
            if fields:
                updates.append((assessment, fields))
        if not updates:
            self.stdout.write('Nada a mudar: as avaliacoes ja tem sexo e altura.')
            return

        for assessment, fields in updates:
            self.stdout.write(self._describe(assessment, fields))
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('--dry-run: nada foi gravado.'))
            return

        with transaction.atomic():
            for assessment, fields in updates:
                for name, value in fields.items():
                    setattr(assessment, name, value)
                assessment.save(update_fields=list(fields))

        resolved_sex = plan.assessment_sex or sex
        resolved_height = plan.height_cm or height_cm
        latest = PublicWorkoutAssessment.objects.filter(plan_slug=plan_slug).order_by('measured_at', 'pk').last()
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

    def _changes(self, assessment, *, plan, sex, height_cm, age) -> dict:
        fields = {}
        if not assessment.sex:
            fields['sex'] = sex
        if height_cm is not None and assessment.height_cm is None:
            fields['height_cm'] = Decimal(str(height_cm))

        # Calculado pela formula masculina padrao: sem sexo gravado e sem
        # sexo no catalogo. So muda o numero quando o sexo real e feminino.
        computed_without_sex = assessment.body_fat_source in _SKINFOLD_SOURCES and not assessment.sex
        if computed_without_sex and not plan.assessment_sex and sex == Sex.FEMALE:
            if age is None:
                raise CommandError(
                    f'{assessment.measured_at}: %gordura de dobras foi calculado com a formula masculina — '
                    'informe --age (idade nessa data) pra recalcular.'
                )
            skinfolds = parse_skinfold_note(assessment.notes)
            body_fat, source = skinfold_body_fat(sex=sex, age=age, skinfolds=skinfolds)
            if body_fat is None:
                raise CommandError(
                    f'{assessment.measured_at}: nao deu pra recalcular com as dobras gravadas ({skinfolds or "nenhuma"}).'
                )
            fields['body_fat_percent'] = Decimal(str(round(body_fat, 1)))
            fields['body_fat_source'] = source
        return fields

    def _describe(self, assessment, fields) -> str:
        parts = []
        if 'sex' in fields:
            parts.append(f'sexo {fields["sex"]}')
        if 'height_cm' in fields:
            parts.append(f'altura {fields["height_cm"]} cm')
        if 'body_fat_percent' in fields:
            parts.append(
                f'%gordura {assessment.body_fat_percent} -> {fields["body_fat_percent"]} ({fields["body_fat_source"]})'
            )
        return f'  {assessment.measured_at}: ' + ', '.join(parts)
