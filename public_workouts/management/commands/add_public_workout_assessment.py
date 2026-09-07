"""
ARQUIVO: comando pra lancar uma avaliacao fisica de um treino publico.

POR QUE ELE EXISTE:
- a aba Avaliacoes nao tem formulario publico de escrita (decisao de
  produto: quem mede e o treinador, nao o aluno pela pagina). Este comando
  e o unico jeito de gravar um registro novo — roda localmente ou na VPS.

FONTE DO %GORDURA (prioridade, da mais pra menos precisa):
1. --bodyfat: numero ja pronto (ex.: leitura de bioimpedancia — use com
   --bodyfat-source device).
2. Dobras cutaneas, protocolo de 7 dobras de Jackson-Pollock (--dobra-peitoral/
   --dobra-axilar/--dobra-triceps/--dobra-subescapular/--dobra-abdomen/
   --dobra-iliaca/--dobra-coxa + --age): usada sempre que as 7 dobras
   estiverem presentes — e o protocolo preferido, mais preciso que o de 3.
3. Dobras cutaneas, protocolo de 3 dobras (mesmas dobras acima, so que faltando
   a axilar): peitoral+abdomen+coxa no homem, triceps+iliaca+coxa na mulher —
   fallback quando nao ha as 7 dobras completas.
4. Nenhum dos anteriores: o relatorio cai pra estimativa por fita (US Navy),
   calculada em tempo real a partir de pescoco/cintura/quadril.

EXEMPLO (medida por fita):
  python manage.py add_public_workout_assessment rafael --date 2026-09-06 \\
      --weight 70 --pescoco 38 --cintura 82 --peito 98 --braco 34 \\
      --coxa 55 --panturrilha 37

EXEMPLO (bioimpedancia):
  python manage.py add_public_workout_assessment rafael --date 2024-12-23 \\
      --bodyfat 8.1 --bodyfat-source device --notes "SmartFit Body: massa muscular 35.30kg"

EXEMPLO (dobras — 7 pontos, mulher):
  python manage.py add_public_workout_assessment franciele --date 2026-09-02 \\
      --weight 66 --age 24 --cintura 83 --quadril 98 --ombro 102 --abdomen 73.5 \\
      --braco 30.75 --coxa 51.15 --panturrilha 33.75 \\
      --dobra-triceps 20 --dobra-iliaca 13 --dobra-coxa 27 --dobra-subescapular 13 \\
      --dobra-abdomen 26 --dobra-peitoral 8 --dobra-axilar 15
"""

from __future__ import annotations

from datetime import date

from django.core.management.base import BaseCommand, CommandError

from public_workouts.formulas import (
    Sex,
    estimate_body_fat_jackson_pollock_3site,
    estimate_body_fat_jackson_pollock_7site,
)
from public_workouts.services import UnknownPlanSlugError, build_report, record_assessment

_MEASUREMENT_FLAGS = ('pescoco', 'cintura', 'abdomen', 'quadril', 'ombro', 'peito', 'braco', 'coxa', 'panturrilha')
_SKINFOLD_FLAGS = ('triceps', 'subescapular', 'abdomen', 'iliaca', 'coxa', 'peitoral', 'axilar')


class Command(BaseCommand):
    help = 'Registra uma avaliacao fisica (peso/medidas) de um plano do corredor publico de treinos.'

    def add_arguments(self, parser):
        parser.add_argument('plan_slug', help='Slug do plano em PUBLIC_WORKOUT_LIBRARY (ex.: rafael)')
        parser.add_argument('--date', dest='measured_at', required=True, help='Data da avaliacao, formato AAAA-MM-DD')
        parser.add_argument('--weight', dest='weight_kg', type=float, default=None, help='Peso em kg')
        parser.add_argument('--age', dest='age', type=float, default=None, help='Idade — so usada no calculo de dobras cutaneas')
        parser.add_argument(
            '--bodyfat',
            dest='body_fat_percent',
            type=float,
            default=None,
            help='%%gordura ja pronto (ex.: leitura de bioimpedancia) — maior prioridade de todas as fontes',
        )
        parser.add_argument(
            '--bodyfat-source',
            dest='body_fat_source',
            default='device',
            help="Rotulo de origem do --bodyfat pro relatorio (default 'device')",
        )
        parser.add_argument('--notes', dest='notes', default='', help='Observacoes livres')
        for flag in _MEASUREMENT_FLAGS:
            parser.add_argument(f'--{flag}', dest=flag, type=float, default=None, help=f'Circunferencia de {flag} em cm')
        for flag in _SKINFOLD_FLAGS:
            parser.add_argument(
                f'--dobra-{flag}', dest=f'dobra_{flag}', type=float, default=None, help=f'Dobra cutanea de {flag} em mm'
            )

    def handle(self, *args, **options):
        plan_slug = options['plan_slug'].strip().lower()
        try:
            measured_at = date.fromisoformat(options['measured_at'])
        except ValueError as exc:
            raise CommandError(f'Data invalida: {options["measured_at"]!r} (use AAAA-MM-DD)') from exc

        from student_app.views.public_workout_views import PUBLIC_WORKOUT_LIBRARY

        try:
            plan = PUBLIC_WORKOUT_LIBRARY[plan_slug]
        except KeyError as exc:
            raise CommandError(f'Plano publico desconhecido: {plan_slug!r}') from exc

        measurements = {flag: options[flag] for flag in _MEASUREMENT_FLAGS if options[flag] is not None}

        notes = options['notes']
        skinfolds = {flag: options[f'dobra_{flag}'] for flag in _SKINFOLD_FLAGS if options[f'dobra_{flag}'] is not None}
        if skinfolds:
            skinfold_note = 'Dobras (mm): ' + ', '.join(f'{k}={v}' for k, v in skinfolds.items())
            notes = f'{notes} {skinfold_note}'.strip()

        body_fat_percent = options['body_fat_percent']
        body_fat_source = options['body_fat_source'] if body_fat_percent is not None else ''

        if body_fat_percent is None and options['age']:
            sex = plan.assessment_sex or Sex.MALE
            septet = (
                skinfolds.get('peitoral'),
                skinfolds.get('axilar'),
                skinfolds.get('triceps'),
                skinfolds.get('subescapular'),
                skinfolds.get('abdomen'),
                skinfolds.get('iliaca'),
                skinfolds.get('coxa'),
            )
            if all(v is not None for v in septet):
                computed = estimate_body_fat_jackson_pollock_7site(
                    sex=sex,
                    age=options['age'],
                    chest_mm=septet[0],
                    midaxillary_mm=septet[1],
                    triceps_mm=septet[2],
                    subscapular_mm=septet[3],
                    abdomen_mm=septet[4],
                    suprailiac_mm=septet[5],
                    thigh_mm=septet[6],
                )
                if computed is not None:
                    body_fat_percent = computed
                    body_fat_source = 'skinfold_jp7'

            if body_fat_percent is None:
                trio = (
                    (skinfolds.get('triceps'), skinfolds.get('iliaca'), skinfolds.get('coxa'))
                    if sex == Sex.FEMALE
                    else (skinfolds.get('peitoral'), skinfolds.get('abdomen'), skinfolds.get('coxa'))
                )
                if all(v is not None for v in trio):
                    computed = estimate_body_fat_jackson_pollock_3site(
                        sex=sex, age=options['age'], fold_a_mm=trio[0], fold_b_mm=trio[1], fold_c_mm=trio[2]
                    )
                    if computed is not None:
                        body_fat_percent = computed
                        body_fat_source = 'skinfold_jp3'

        try:
            record_assessment(
                plan_slug=plan_slug,
                measured_at=measured_at,
                weight_kg=options['weight_kg'],
                body_fat_percent=body_fat_percent,
                body_fat_source=body_fat_source,
                measurements=measurements,
                notes=notes,
            )
        except UnknownPlanSlugError as exc:
            raise CommandError(str(exc)) from exc

        report = build_report(plan_slug=plan_slug, sex=plan.assessment_sex, height_cm=plan.height_cm)

        self.stdout.write(self.style.SUCCESS(f'Avaliacao registrada: {plan_slug} @ {measured_at.isoformat()}'))
        indicators = report['indicators'] or {}
        if indicators.get('bmi'):
            self.stdout.write(f'  IMC: {indicators["bmi"]["value"]} ({indicators["bmi"]["classification"]["label"]})')
        if indicators.get('whr'):
            self.stdout.write(f'  RCQ: {indicators["whr"]["value"]} ({indicators["whr"]["classification"]["label"]})')
        if indicators.get('body_fat_percent'):
            bf = indicators['body_fat_percent']
            self.stdout.write(f'  %Gordura ({bf["source"]}): {bf["value"]}% ({bf["classification"]["label"]})')
        if report['summary'] and report['summary']['count'] > 1:
            self.stdout.write(f'  Historico: {report["summary"]["count"]} avaliacoes registradas.')
