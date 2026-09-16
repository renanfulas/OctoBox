"""
COMANDO: upgrade_periodization_model

POR QUE EXISTE:
- Onda B3+ do CORDA (docs/plans/public-workouts-produtizacao-corda.md,
  "Periodização canônica") — acrescenta `periodization.weeks` (vocabulário
  fechado, ver `public_workouts/periodization.py::PHASE_PROFILES`) ao
  payload JÁ PUBLICADO de um cliente, mapeando o `chart` livre que ele já
  tem pras 6 fases canônicas. Aditivo (schema.py): `chart`/`weeks_table`
  continuam intactos, `weeks` só se soma.
- Escopo inicial era só a Juliana (prova de conceito). Auditoria posterior
  (pedido do Renan: "pegue todos os treinos e corrija a periodização...
  com o gráfico etc") cobriu as outras 9 e migrou mais 3 (henrique/john/
  milene) cujo `weeks_table` real é uma progressão de mesociclo compatível
  com o vocabulário fechado. As outras 6 ficam de fora de propósito (ver
  comentário de `CURATED_WEEKS_MAPPING`) — não é trabalho pendente, é
  conteúdo que genuinamente não é periodização de força por %RM (CrossFit
  metabólico, corte com manutenção, progressão de corrida, ritmo semanal,
  ou nenhuma aba de periodização no HTML). Migrar giovanna/bruno no
  futuro depende de decidir explicitamente sobre novo(s) phase_type
  (Manutenção/Teste pro bruno) e se vale forçar CrossFit num modelo
  pensado pra força linear (giovanna) — proposta ao Renan, não decisão
  unilateral. franciele/rafael/johnespanha/thaislima não têm conteúdo
  compatível de jeito nenhum (corrida/ritmo semanal/nada).

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

# Mapeamento manual, conferido contra o `weeks_table`/`chart` real já
# publicado de cada cliente (S1..S6 na ordem de aparição) -- decisão de
# leitura humana, nunca adivinhação automática (ver docstring do módulo).
# Auditoria desta fatia (pedido do Renan: "pegue todos os treinos e
# corrija a periodização... com o gráfico etc"): das 9 clientes restantes,
# só 3 têm um `weeks_table` que descreve de verdade uma progressão de
# MESOCICLO compatível com os 6 `phase_type` fechados de
# `periodization.PHASE_PROFILES` -- as outras 6 ficam de fora desta
# curadoria por não caber no modelo sem forçar (ver "Achados desta
# auditoria" abaixo, não são bugs, são conteúdo genuinamente diferente):
#
# - giovanna: vocabulário de CrossFit ("Base técnica"/"Sobrecarga"/
#   "Metabólico"/"Peak controlado") -- a semana "Metabólico" (AMRAP/
#   condicionamento) não tem um %RM-alvo real, forçar num phase_type
#   baseado em %RM daria sugestão de carga ERRADA pra essa semana.
# - bruno: bloco de CORTE ("a meta não é progredir carga — é segurar a
#   carga enquanto o peso corporal cai"). "Manutenção" (×3 semanas) e
#   "Teste" não existem no vocabulário fechado hoje -- migrar exigiria
#   PROPOR phase_type novo ao Renan primeiro (mesma regra já documentada
#   no plano: "se o objetivo do bloco não encaixa em nenhuma chave
#   existente, é sinal de que PHASE_PROFILES precisa crescer, não de
#   inventar"). Fica pendente de decisão, não migrado nesta fatia.
# - franciele: `weeks_table` é uma progressão de CORRIDA (caminhada ->
#   trote -> corrida contínua), não uma periodização de força -- o
#   modelo de %RM/RIR simplesmente não se aplica.
# - rafael: `#tab-period` dele descreve o RITMO SEMANAL de treino (Dia
#   A/Descanso/Dia B/Coringa condicional), não fases de mesociclo --
#   conteúdo genuinamente diferente, não um "chart" incompleto.
# - johnespanha/thaislima: HTML não tem `#tab-period` nenhum -- não há
#   dado nenhum pra migrar (nunca tiveram periodização, não é regressão).
CURATED_WEEKS_MAPPING = {
    'juliana': [
        {'week_number': 1, 'phase_type': 'adaptation'},
        {'week_number': 2, 'phase_type': 'volume'},
        {'week_number': 3, 'phase_type': 'strength_hypertrophy'},
        {'week_number': 4, 'phase_type': 'intensity'},
        {'week_number': 5, 'phase_type': 'peak'},
        {'week_number': 6, 'phase_type': 'deload'},
    ],
    'henrique': [
        # 'Pico Máximo' (S5) repete 'peak' de proposito -- guidance real
        # ("carga mais alta em todas as series do ramp") e' um 2o degrau
        # do MESMO pico, nao uma fase nova; nao existe conceito de
        # "pico do pico" no vocabulario fechado.
        {'week_number': 1, 'phase_type': 'adaptation'},
        {'week_number': 2, 'phase_type': 'volume'},
        {'week_number': 3, 'phase_type': 'intensity'},
        {'week_number': 4, 'phase_type': 'peak'},
        {'week_number': 5, 'phase_type': 'peak'},
        {'week_number': 6, 'phase_type': 'deload'},
    ],
    'john': [
        # "Progressão" (S2-S4) repete o MESMO rotulo no HTML mas cada
        # semana tem um incremento absoluto diferente e crescente
        # (+2,5kg / +5kg / +7,5kg vs. S1, todos vs. a MESMA semana base
        # -- nao e' cumulativo) -- mapeado pra 3 fases DIFERENTES e
        # crescentes (volume->forca-hiper->intensidade) pra preservar
        # essa progressao real na sugestao de carga, em vez de achatar
        # as 3 semanas na mesma fase (o que congelaria a sugestao).
        {'week_number': 1, 'phase_type': 'adaptation'},
        {'week_number': 2, 'phase_type': 'volume'},
        {'week_number': 3, 'phase_type': 'strength_hypertrophy'},
        {'week_number': 4, 'phase_type': 'intensity'},
        {'week_number': 5, 'phase_type': 'peak'},
        {'week_number': 6, 'phase_type': 'deload'},
    ],
    'milene': [
        # 'Volume Alto' (S4) repete 'volume' de proposito -- guidance real
        # ("Bomba e estresse metabolico") e' o MESMO eixo de volume da S2,
        # so' que mais alto; nao existe "volume alto" separado no
        # vocabulario fechado.
        {'week_number': 1, 'phase_type': 'adaptation'},
        {'week_number': 2, 'phase_type': 'volume'},
        {'week_number': 3, 'phase_type': 'strength_hypertrophy'},
        {'week_number': 4, 'phase_type': 'volume'},
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
