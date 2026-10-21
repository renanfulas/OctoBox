"""
ARQUIVO: comando pra lancar uma avaliacao fisica de um treino publico.

POR QUE ELE EXISTE:
- e o unico jeito de gravar uma avaliacao PRESENCIAL (Jackson-Pollock,
  com o treinador e o adipometro, ou bioimpedancia) — roda localmente ou
  na VPS. A partir da Onda A3/B4, a pagina TEM formulario publico de
  escrita (PublicWorkoutRecordAssessmentView, POST /renan/<slug>/avaliacoes):
  US Navy (so fita) sempre; dobras cutaneas de 7 pontos tambem, mas so
  depois que este comando lancar a primeira avaliacao por dobra do plano
  (`has_presencial_skinfold_assessment` — decisao do Renan: so confia na
  tecnica do aluno pinçando a dobra sozinho apos ele ja ter sido
  calibrado ao vivo pelo menos uma vez).

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

SEXO E ALTURA (--sex F|M, --height cm):
- ficam gravados na avaliacao e dao ao aluno o relatorio completo (IMC, RCQ,
  %gordura com classificacao) — o mesmo da Franciele, que tem os dois no
  catalogo fixo. So precisa informar na 1a vez: as avaliacoes seguintes
  herdam o ultimo valor gravado. O catalogo, quando declara, sempre vence.
- dobras cutaneas EXIGEM o sexo conhecido: a formula de Jackson-Pollock e
  diferente pra homem e mulher. Antes caia na masculina sem avisar.

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

EXEMPLO (dobras — aluno sem sexo/altura no catalogo, 1a avaliacao):
  python manage.py add_public_workout_assessment <slug> --date 2026-10-15 \\
      --sex F --height 165 --weight 61 --age 31 --cintura 70 --quadril 96 \\
      --dobra-triceps 18 --dobra-iliaca 12 --dobra-coxa 24 --dobra-subescapular 11 \\
      --dobra-abdomen 20 --dobra-peitoral 7 --dobra-axilar 10
"""

from __future__ import annotations

from datetime import date

from django.core.management.base import BaseCommand, CommandError

from public_workouts.catalog import PUBLIC_WORKOUT_LIBRARY
from public_workouts.services import (
    AssessmentValueError,
    UnknownPlanSlugError,
    build_report,
    is_known_plan_slug,
    record_assessment,
    resolve_assessment_profile,
    skinfold_body_fat,
)

_MEASUREMENT_FLAGS = ('pescoco', 'cintura', 'abdomen', 'quadril', 'ombro', 'peito', 'braco', 'coxa', 'panturrilha')
_SKINFOLD_FLAGS = ('triceps', 'subescapular', 'abdomen', 'iliaca', 'coxa', 'peitoral', 'axilar')


class Command(BaseCommand):
    help = 'Registra uma avaliacao fisica (peso/medidas) de um plano do corredor publico de treinos.'

    def add_arguments(self, parser):
        parser.add_argument('plan_slug', help='Slug do aluno (catalogo ou programa ativo, ex.: rafael, giulia)')
        parser.add_argument('--date', dest='measured_at', required=True, help='Data da avaliacao, formato AAAA-MM-DD')
        parser.add_argument('--weight', dest='weight_kg', type=float, default=None, help='Peso em kg')
        parser.add_argument('--age', dest='age', type=float, default=None, help='Idade — so usada no calculo de dobras cutaneas')
        parser.add_argument(
            '--sex',
            dest='sex',
            choices=('F', 'M'),
            default=None,
            help='Sexo do aluno (F/M) — obrigatorio pra dobras quando o catalogo nao declara; fica gravado',
        )
        parser.add_argument(
            '--height', dest='height_cm', type=float, default=None, help='Altura em cm (IMC) — fica gravada'
        )
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

        # Catalogo fixo ou aluno novo com programa ativo (fora do catalogo, sem
        # sexo/altura fixos — vem de --sex/--height ou da avaliacao anterior).
        if not is_known_plan_slug(plan_slug):
            raise CommandError(f'Plano publico desconhecido: {plan_slug!r}')
        plan = PUBLIC_WORKOUT_LIBRARY.get(plan_slug)
        plan_sex = plan.assessment_sex if plan else None
        plan_height_cm = plan.height_cm if plan else None

        measurements = {flag: options[flag] for flag in _MEASUREMENT_FLAGS if options[flag] is not None}

        notes = options['notes']
        skinfolds = {flag: options[f'dobra_{flag}'] for flag in _SKINFOLD_FLAGS if options[f'dobra_{flag}'] is not None}
        if skinfolds:
            skinfold_note = 'Dobras (mm): ' + ', '.join(f'{k}={v}' for k, v in skinfolds.items())
            notes = f'{notes} {skinfold_note}'.strip()

        body_fat_percent = options['body_fat_percent']
        body_fat_source = options['body_fat_source'] if body_fat_percent is not None else ''

        # Catalogo fixo vence; senao --sex/--height; senao o ultimo valor
        # gravado nas avaliacoes anteriores deste aluno.
        if options['sex'] and plan_sex and options['sex'] != plan_sex:
            raise CommandError(f'--sex {options["sex"]} contradiz o catalogo de {plan_slug!r} ({plan_sex}).')
        profile = resolve_assessment_profile(
            plan_slug=plan_slug,
            plan_sex=plan_sex or options['sex'],
            plan_height_cm=plan_height_cm or options['height_cm'],
        )
        sex, height_cm = profile['sex'], profile['height_cm']

        if body_fat_percent is None and options['age'] and skinfolds:
            if not sex:
                raise CommandError(
                    f'Informe --sex F ou --sex M: {plan_slug!r} ainda nao tem sexo registrado e a formula '
                    'de dobras cutaneas e diferente pra homem e mulher.'
                )
            body_fat_percent, body_fat_source = skinfold_body_fat(sex=sex, age=options['age'], skinfolds=skinfolds)
            if body_fat_percent is None:
                body_fat_source = ''

        try:
            record_assessment(
                plan_slug=plan_slug,
                measured_at=measured_at,
                weight_kg=options['weight_kg'],
                body_fat_percent=body_fat_percent,
                body_fat_source=body_fat_source,
                measurements=measurements,
                notes=notes,
                sex=sex or '',
                height_cm=height_cm,
            )
        except (UnknownPlanSlugError, AssessmentValueError) as exc:
            raise CommandError(str(exc)) from exc

        # Gera e grava o comentario tecnico (hero da aba Avaliacoes) uma
        # unica vez aqui, no momento do lancamento presencial — nunca em
        # GET (ver assessment_hero_ai.py). Falha silenciosa (None) nunca
        # impede a avaliacao de ter sido registrada com sucesso.
        from public_workouts.assessment_hero_ai import generate_and_store_hero_commentary

        hero_text = generate_and_store_hero_commentary(plan_slug=plan_slug, sex=sex, height_cm=height_cm)

        report = build_report(plan_slug=plan_slug, sex=sex, height_cm=height_cm)

        self.stdout.write(self.style.SUCCESS(f'Avaliacao registrada: {plan_slug} @ {measured_at.isoformat()}'))
        if hero_text:
            self.stdout.write(f'  Comentario (hero): {hero_text}')
        else:
            self.stdout.write('  Comentario (hero): nao gerado (sem ANTHROPIC_API_KEY, timeout, ou erro).')
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
