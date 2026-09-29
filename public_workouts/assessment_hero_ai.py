"""
ARQUIVO: geracao do comentario tecnico (hero) da aba Avaliacoes via LLM
(Claude Haiku).

POR QUE ELE EXISTE:
- `build_report` (services.py) so calcula os INDICADORES deterministicos
  (IMC/RCQ/%gordura + classificacao) — mesma fronteira de
  `weekly_review_ai.py` (services.py nunca importa cliente de IA, ver
  `test_never_calls_an_ai_provider` em test_weekly_review.py). Este modulo
  e onde a chamada de IA de verdade mora.
- DIFERENTE do weekly review (que e' sob demanda, clique em "Gerar
  revisao", nunca no GET principal): aqui o texto e' gerado UMA VEZ, no
  momento em que a avaliacao e registrada (management command
  `add_public_workout_assessment`), e gravado no proprio registro
  (`PublicWorkoutAssessment.hero_commentary`). `PublicWorkoutAssessmentsView`
  (GET /avaliacoes.json) so LE esse campo ja calculado — nunca chama a IA
  em tempo de leitura. Isso evita tanto o custo/latencia de LLM por
  page-load (mesmo principio do weekly review) quanto a necessidade de um
  botao "gerar" na tela, ja que avaliacao presencial e' um evento raro
  (nao uma pagina visitada toda hora).
- Escopo deliberado: so a avaliacao PRESENCIAL (management command) gera
  o hero. A autoavaliacao online (PublicWorkoutRecordAssessmentView, POST)
  nao chama isto — adicionar 10s de latencia sincrona a um POST de
  formulario do proprio aluno e' um trade-off diferente, nao decidido
  ainda; ver nota no docstring da view.

O QUE ESTE ARQUIVO FAZ:
1. recebe o dict `indicators` que `build_report` ja calculou (bmi/whr/
   body_fat_percent, cada um com value/classification/delta) — nunca
   consulta o banco pra calcular nada aqui.
2. chama a Anthropic (Claude Haiku) com esses sinais, pede um comentario
   tecnico curto em PT-BR, tom de profissional (nutricionista/personal)
   avaliando o aluno.
3. falha graciosamente (retorna `None`, nunca levanta excecao) sem chave
   configurada, sem indicador nenhum pra comentar, timeout, erro HTTP ou
   resposta vazia — a aba de avaliacao nunca quebra por causa da IA.

PONTOS CRITICOS:
- Mesmo padrao HTTP de `weekly_review_ai.py`: `requests` cru, NAO o SDK
  `anthropic`. Mesma env var `ANTHROPIC_API_KEY` via `os.getenv` direto.
- O prompt pede explicitamente pra nunca inventar numero fora do dict
  recebido, e pra nunca contradizer a classificacao (`label`/`level`) ja
  calculada — o texto so descreve o que os indicadores ja dizem.
- Tom deliberadamente educativo/geral (ex.: "RCQ dentro da faixa associada
  a menor risco cardiovascular"), nunca diagnostico medico individual —
  isto e' comentario de acompanhamento fitness, nao laudo clinico.
"""

from __future__ import annotations

import logging
import os

import requests

logger = logging.getLogger(__name__)

_ANTHROPIC_MESSAGES_URL = 'https://api.anthropic.com/v1/messages'
_ANTHROPIC_API_VERSION = '2023-06-01'
_ANTHROPIC_MODEL = 'claude-haiku-4-5-20251001'
_TIMEOUT_SECONDS = 10

_SYSTEM_PROMPT = (
    'Voce e um profissional (nutricionista/personal trainer) comentando a '
    'avaliacao fisica de um aluno pra ele mesmo ler no app. Voce recebe SO '
    'indicadores ja calculados (IMC, RCQ, %gordura — cada um com valor, '
    'classificacao e variacao desde a 1a avaliacao quando disponivel) — '
    'nunca invente numero que nao esteja nos dados recebidos, e nunca '
    'contradiga a classificacao ja calculada (ex.: nao chame de "risco" um '
    'indicador classificado como "good").\n\n'
    'Responda em portugues do Brasil, 3 a 4 frases, tom profissional e '
    'encorajador (nao robotico, nao generico, nao alarmista). Pode '
    'explicar brevemente o que cada indicador significa na pratica (ex.: '
    'RCQ controlado associa-se a menor risco cardiovascular) mas isto e '
    'um comentario de acompanhamento fitness, NUNCA um diagnostico '
    'medico — nao mencione doencas especificas do aluno nem faca '
    'prescricao clinica. Se houver evolucao (delta) desde a 1a avaliacao, '
    'destaque isso.'
)


def generate_assessment_hero_text(indicators: dict) -> str | None:
    """Transforma o dict `indicators` de `build_report` num comentario curto.

    `indicators` e exatamente `report['indicators']` (retorno de
    `public_workouts.services.build_report`) — este modulo nunca consulta
    o banco, so formata o que ja veio calculado.

    Retorna `None` (nunca levanta excecao) sem `ANTHROPIC_API_KEY`
    configurada, sem nenhum indicador pra comentar, timeout, erro HTTP ou
    resposta vazia.
    """
    if not indicators or not any(indicators.get(key) for key in ('bmi', 'whr', 'body_fat_percent')):
        return None

    api_key = os.getenv('ANTHROPIC_API_KEY', '').strip()
    if not api_key:
        logger.debug('assessment_hero_ai: ANTHROPIC_API_KEY nao configurada.')
        return None

    user_message = f'Indicadores da avaliacao mais recente: {indicators}'

    try:
        response = requests.post(
            _ANTHROPIC_MESSAGES_URL,
            headers={
                'x-api-key': api_key,
                'anthropic-version': _ANTHROPIC_API_VERSION,
                'Content-Type': 'application/json',
            },
            json={
                'model': _ANTHROPIC_MODEL,
                'max_tokens': 300,
                'system': _SYSTEM_PROMPT,
                'messages': [{'role': 'user', 'content': user_message}],
            },
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        logger.warning('assessment_hero_ai: chamada a Anthropic falhou: %s', exc)
        return None

    parts = [block.get('text', '') for block in data.get('content', []) if block.get('type') == 'text']
    text = '\n'.join(parts).strip()
    return text or None


def generate_and_store_hero_commentary(*, plan_slug: str, sex: str | None, height_cm: float | None) -> str | None:
    """Gera o comentario pra avaliacao mais recente de `plan_slug` e grava
    em `PublicWorkoutAssessment.hero_commentary`.

    Chamado uma unica vez, logo apos `services.record_assessment(...)`
    (hoje so pelo management command `add_public_workout_assessment` — ver
    docstring do modulo). Nunca chamado em request GET.

    Retorna o texto gerado (ou `None` se a IA nao respondeu/falhou) — quem
    chama pode usar o retorno so pra feedback no terminal, o valor
    relevante ja foi persistido no banco.
    """
    from public_workouts.models import PublicWorkoutAssessment
    from public_workouts.services import build_report, list_assessments

    report = build_report(plan_slug=plan_slug, sex=sex, height_cm=height_cm)
    indicators = report.get('indicators')
    if not indicators:
        return None

    hero_text = generate_assessment_hero_text(indicators)

    assessments = list_assessments(plan_slug=plan_slug)
    if not assessments:
        return None
    latest = assessments[-1]
    PublicWorkoutAssessment.objects.filter(pk=latest.pk).update(hero_commentary=hero_text)
    return hero_text


__all__ = ['generate_assessment_hero_text', 'generate_and_store_hero_commentary']
