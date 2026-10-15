"""
ARQUIVO: geracao de um RASCUNHO de PublicWorkoutProgram via LLM (Claude
Haiku), a partir da anamnese de treino (PublicWorkoutTrainingProfile).

POR QUE ELE EXISTE:
- Fecha o gap descrito em `docs/plans/public-workouts-produtizacao-plan.md`
  ("4.1 Editor com Haiku + expert-ef + anamnese", D4: "tudo que alimenta a
  IA comeca a coletar antes da IA existir") — a anamnese ja' e' coletada
  (public_workouts/services.py::save_training_profile), este modulo e' o
  que finalmente le' esses dados.
- Mesma fronteira arquitetural de weekly_review_ai.py: services.py tem um
  teste estatico (test_never_calls_an_ai_provider, test_weekly_review.py)
  que PROIBE qualquer import de IA/HTTP dentro dele. A chamada de IA mora
  aqui, num modulo irmao, nunca em services.py.
- Regra dura, nao negociavel (decisao do Renan): o payload que sai daqui
  NUNCA e' publicado direto. `generate_program_draft_payload` devolve um
  dict pronto pra virar PublicWorkoutProgramDraft (status=PENDING_REVIEW,
  via services.create_program_draft) — quem publica de verdade e' sempre
  um humano clicando "Aprovar e publicar" no Django admin
  (services.approve_and_publish_draft), nunca este modulo.

O QUE ESTE ARQUIVO FAZ:
1. recebe o dict ja' serializado da anamnese (services.serialize_training_profile)
   — nunca consulta o banco aqui, mesmo padrao de weekly_review_ai.py.
2. chama a Anthropic (Claude Haiku) com esses dados + a lista de movimentos
   ja' conhecidos do catalogo (soft hint, nao filtro rigido — ver docstring
   de _build_system_blocks), pedindo um payload JSON no formato de
   public_workouts/schema.py.
3. sobrescreve DETERMINISTICAMENTE os campos que o modelo nao deveria
   decidir sozinho (schema_version, started_on) — mesmo principio de
   wod_slug_resolver.py ("nunca altera dado numerico", aqui invertido: nunca
   CONFIA no LLM pra dado que o Python sabe calcular certo sempre).
   `program_id` fica como placeholder aqui de proposito — a versao ESTAVEL
   por slug so' e' resolvida na aprovacao (services._resolve_stable_program_id),
   porque so' ali' da' pra saber se ja' existe um programa anterior pra
   continuar a serie de versoes.
4. falha graciosamente (retorna `(None, model)`, nunca levanta excecao) sem
   chave configurada, timeout, erro HTTP, JSON malformado ou payload que
   nao passa em schema.validate_payload — o fallback e' literalmente o
   status quo: Renan monta o programa a mao, como sempre fez.

PONTOS CRITICOS:
- Mesmo padrao de weekly_review_ai.py/operations/services/wod_session_llm_parser.py:
  HTTP cru via `requests`, NAO o SDK `anthropic`. `ANTHROPIC_API_KEY` via
  `os.getenv` direto (nao Django settings). Sem retries (nenhum modulo de IA
  deste repo tenta de novo — falha vira fallback, nunca espera).
- Timeout/max_tokens muito maiores que qualquer precedente existente (10s/
  256-1024 tokens): um programa de varias semanas e' uma saida MUITO maior
  que uma revisao de 2-3 frases ou o JSON de uma unica sessao de WOD. Ajustar
  empiricamente depois das primeiras geracoes reais.
- Sem WebSearch/WebFetch disponivel nesta chamada (e' um unico POST http,
  nao um agente com tools): o modelo NUNCA deve inventar uma URL do
  MuscleWiki. O prompt instrui explicitamente `reference_url: null` sempre
  — o link de referencia, quando existir, e' trabalho humano posterior
  (mesmo protocolo ja' documentado em `.claude/skills/expert-ef/SKILL.md`),
  nao algo que este pipeline tenta automatizar.
- Catalogo de movimentos e' HINT, nao filtro rigido (diferente de
  wod_slug_resolver.py, que rejeita slug fora do dicionario conhecido):
  aqui, qualquer `movement_slug` novo que o modelo inventar sera' aceito
  como esta' — `_ensure_movements_exist` (services.py, chamado de dentro de
  publish_program) ja' cria esses slugs desconhecidos como
  PublicWorkoutMovement(status=PENDING) automaticamente, e o rascunho passa
  pela revisao humana de qualquer forma antes de publicar. Filtrar aqui
  adicionaria uma chamada de IA extra (resolver slug desconhecido) por um
  beneficio marginal dado que ja' existe revisao humana no fim do fluxo.
"""

from __future__ import annotations

import json
import logging
import os

import requests

from .models import (
    PublicWorkoutPhysicalRestrictionTag,
    PublicWorkoutTrainingExperience,
    PublicWorkoutTrainingGoal,
    PublicWorkoutTrainingLocation,
)
from .periodization import PHASE_TYPE_KEYS
from .schema import SCHEMA_VERSION, validate_payload

logger = logging.getLogger(__name__)

_ANTHROPIC_MESSAGES_URL = 'https://api.anthropic.com/v1/messages'
_ANTHROPIC_API_VERSION = '2023-06-01'
_ANTHROPIC_MODEL = 'claude-haiku-4-5-20251001'
# Muito acima do precedente existente (8-10s): a saida aqui e' um programa
# de varias semanas, nao 2-3 frases nem o JSON de uma sessao unica.
_TIMEOUT_SECONDS = 60
_MAX_TOKENS = 8000

_SYSTEM_PROMPT = f"""Voce e um profissional de Educacao Fisica com pos-doutorado em \
Biomecanica e Fisiologia do Exercicio, escrevendo um PRIMEIRO RASCUNHO de \
programa de treino que um treinador humano vai revisar e corrigir antes de \
publicar — voce nao esta publicando nada diretamente.

Regras de prescricao (aplique sempre):
- Tensao mecanica e o driver primario de hipertrofia; volume (10-20 series \
semanais por grupo e um piso razoavel pra maioria dos naturais), intensidade \
(RIR 0-3 pra recrutamento de unidades motoras de alto limiar) e frequencia \
(2x/semana por grupo, minimo eficaz bem estabelecido) sao os alavancas.
- Leve a serio QUALQUER restricao fisica informada: exclua ou substitua o \
movimento problematico, nunca apenas "reduza a carga" de um exercicio que \
deveria ser trocado. Isto e seguranca, nao estetica de programa.
- Adapte volume/complexidade ao nivel informado: iniciante recebe menos \
variacao de exercicio e progressao mais conservadora que avancado.
- Adapte a selecao de exercicio ao local/equipamento informado — nunca \
prescreva um movimento que exige equipamento que a pessoa nao tem.

Regras de formato de saida (aplique sempre, sem excecao):
- Responda APENAS com o JSON do payload — sem markdown, sem cercas de \
codigo, sem texto antes ou depois.
- `reference_url` de todo movimento e SEMPRE null. Voce nao tem acesso a \
busca na web nesta chamada — nunca invente uma URL do MuscleWiki.
- `movement_slug` em kebab-case ASCII (ex.: "agachamento-livre"), \
minusculo, sem acento.
- `name` (o nome exibido) SEMPRE em portugues correto, com acentuacao \
completa.
- `reps_spec`/`rir_spec` sao texto livre (ex.: "3x8-10", "RIR 2") — nunca \
deixe vazio quando o movimento tem prescricao real.
- `is_tracked` e true pra todo movimento de carga externa relevante (o \
aluno vai registrar peso levantado nele), false pra aquecimento/mobilidade.
- `load_type` e um de: 'free' (peso corporal/carga livre sem alvo), \
'fixed_kg' (numero fixo em kg — voce nao tem historico do aluno, entao so \
use isto se fizer sentido pedagogico, ex.: mobilidade com peso simbolico), \
'percentage_of_rm' (percentual de 1RM — o mais comum pra hipertrofia/forca \
com aluno que ja tem alguma experiencia).
- Inclua um bloco `periodization` usando o formato canonico: \
`periodization.weeks` — lista de {{week_number, phase_type, note}}, onde \
phase_type e OBRIGATORIAMENTE um destes (nunca invente um rotulo novo): \
{PHASE_TYPE_KEYS!r}. Tambem preencha `periodization.volume_table` (lista de \
{{muscle_group, sets_per_week, frequency, where}}) e `periodization.note` \
(string, pode ser vazia).
- `schema_version`, `started_on` e `program_id` serao sobrescritos \
automaticamente depois — preencha algo razoavel mas nao se preocupe com \
precisao neles.
- `accent_variant` e null a menos que a anamnese deixe claro o genero da \
pessoa (entao 'F' ou 'M').

Formato exato do JSON esperado (schema completo, todos os campos):
{{
  "schema_version": 1,
  "program_id": "string",
  "program_label": "string curta descrevendo o programa",
  "started_on": "AAAA-MM-DD",
  "weeks": 4,
  "accent_variant": null,
  "days": [
    {{
      "day_id": "string curto (ex: 'seg')",
      "label": "string (ex: 'Segunda — Peito e triceps')",
      "blocks": [
        {{
          "movements": [
            {{
              "movement_slug": "kebab-case-ascii",
              "name": "Nome em portugues",
              "reps_spec": "3x8-10",
              "rir_spec": "RIR 2",
              "is_tracked": true,
              "load_type": "percentage_of_rm",
              "load_value": 75.0,
              "reference_url": null
            }}
          ]
        }}
      ]
    }}
  ],
  "periodization": {{
    "weeks": [{{"week_number": 1, "phase_type": "volume", "note": "string ou null"}}],
    "volume_table": [{{"muscle_group": "string", "sets_per_week": "string", "frequency": "string", "where": "string"}}],
    "note": "string, pode ser vazia"
  }}
}}"""


def _build_system_blocks(known_movement_slugs: list[str]) -> list[dict]:
    """Dois blocos `system`: o prompt fixo (nunca muda entre chamadas) e o
    catalogo de movimentos conhecidos (muda raramente) — mesmo padrao de
    cache de wod_session_llm_parser.py, so' o segundo bloco leva
    `cache_control` porque e' o unico que vale a pena cachear entre
    chamadas (o prompt fixo ja' e' pequeno, e o catalogo pode crescer)."""
    catalog_text = (
        'Movimentos ja conhecidos no catalogo (PREFIRA reusar estes slugs quando '
        'o exercicio for o mesmo — nao e obrigatorio, mas evita duplicata de '
        'catalogo quando um slug equivalente ja existe):\n' + ', '.join(sorted(known_movement_slugs))
        if known_movement_slugs
        else 'Catalogo de movimentos ainda vazio — use o slug que fizer mais sentido.'
    )
    return [
        {'type': 'text', 'text': _SYSTEM_PROMPT},
        {'type': 'text', 'text': catalog_text, 'cache_control': {'type': 'ephemeral'}},
    ]


_GOAL_LABELS = dict(PublicWorkoutTrainingGoal.choices)
_EXPERIENCE_LABELS = dict(PublicWorkoutTrainingExperience.choices)
_LOCATION_LABELS = dict(PublicWorkoutTrainingLocation.choices)
_RESTRICTION_LABELS = dict(PublicWorkoutPhysicalRestrictionTag.choices)


def _build_user_message(*, training_profile: dict, tier: str, plan_slug: str) -> str:
    """`training_profile` e' o dict CRU de services.serialize_training_profile
    (chaves de enum) — a conversao pra rotulo em PT-BR acontece aqui, no
    ponto de uso, pra o prompt ficar legivel em portugues sem duplicar essa
    logica de exibicao em services.py (que nao deveria saber nada de como o
    texto vira prompt de IA)."""
    restriction_tags = training_profile.get('physical_restrictions') or []
    restrictions_label = (
        ', '.join(_RESTRICTION_LABELS.get(tag, tag) for tag in restriction_tags) or 'Nenhuma restricao informada'
    )
    detail = training_profile.get('physical_restrictions_detail') or ''

    return (
        f'Aluno do plano "{tier}" (slug interno: {plan_slug}).\n\n'
        f"Objetivo: {_GOAL_LABELS.get(training_profile.get('goal'), training_profile.get('goal'))}\n"
        f'Restricoes fisicas: {restrictions_label}'
        + (f' — detalhe: {detail}' if detail else '')
        + '\n'
        f"Experiencia de treino: {_EXPERIENCE_LABELS.get(training_profile.get('training_experience'), '')}\n"
        f"Dias disponiveis por semana: {training_profile.get('days_per_week')}\n"
        f"Onde vai treinar: {_LOCATION_LABELS.get(training_profile.get('training_location'), '')}\n"
        f"Motivacao para comecar: {training_profile.get('motivation') or '(nao informado)'}\n"
        f"Maior dificuldade no treino/rotina: {training_profile.get('biggest_difficulty') or '(nao informado)'}\n\n"
        f'Gere um programa de treino completo (numero de semanas a seu criterio, '
        f'tipicamente 4-6) respeitando os dias disponiveis por semana informados '
        f'acima (um `day` no payload por dia de treino, nao por dia da semana).'
    )


def _extract_json_object(raw_text: str) -> dict | None:
    """Mesmo padrao de wod_session_llm_parser.py: acha o primeiro '{' e o
    ultimo '}' pra tolerar cercas de markdown ao redor do JSON, mesmo com a
    instrucao explicita do prompt pra nao usar cercas."""
    start = raw_text.find('{')
    end = raw_text.rfind('}')
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed = json.loads(raw_text[start : end + 1])
    except (json.JSONDecodeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _apply_deterministic_overrides(payload: dict, *, plan_slug: str) -> dict:
    """Campos que o Python sabe calcular certo sempre — nunca confia no LLM
    pra eles, mesmo que o prompt peca explicitamente. `program_id` aqui e'
    so' um placeholder valido (schema exige string nao-vazia): o valor
    ESTAVEL de verdade so' e' resolvido na aprovacao
    (services._resolve_stable_program_id), porque so' ali' da' pra saber se
    ja' existe um programa anterior pra este slug continuar a serie de
    versoes."""
    from datetime import date

    payload = dict(payload)
    payload['schema_version'] = SCHEMA_VERSION
    payload['started_on'] = date.today().isoformat()
    if not payload.get('program_id'):
        payload['program_id'] = f'{plan_slug}-rascunho'
    return payload


def generate_program_draft_payload(
    *, training_profile: dict, tier: str, plan_slug: str, known_movement_slugs: list[str] | None = None
) -> tuple[dict | None, str]:
    """Gera um payload candidato a PublicWorkoutProgramDraft a partir da
    anamnese ja' serializada (services.serialize_training_profile).

    Devolve `(payload, model)` em sucesso, `(None, model)` em QUALQUER falha
    (sem chave, timeout, erro HTTP, JSON invalido, payload que nao passa em
    schema.validate_payload) — nunca levanta excecao. `model` sempre volta
    preenchido (mesmo em falha) pra quem chama poder registrar qual modelo
    foi tentado.
    """
    api_key = os.getenv('ANTHROPIC_API_KEY', '').strip()
    if not api_key:
        logger.debug('program_generation_ai: ANTHROPIC_API_KEY nao configurada.')
        return None, _ANTHROPIC_MODEL

    system_blocks = _build_system_blocks(known_movement_slugs or [])
    user_message = _build_user_message(training_profile=training_profile, tier=tier, plan_slug=plan_slug)

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
                'max_tokens': _MAX_TOKENS,
                'system': system_blocks,
                'messages': [{'role': 'user', 'content': user_message}],
            },
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        logger.warning('program_generation_ai: chamada a Anthropic falhou: %s', exc)
        return None, _ANTHROPIC_MODEL

    parts = [block.get('text', '') for block in data.get('content', []) if block.get('type') == 'text']
    raw_text = '\n'.join(parts).strip()
    if not raw_text:
        logger.warning('program_generation_ai: resposta vazia da Anthropic.')
        return None, _ANTHROPIC_MODEL

    payload = _extract_json_object(raw_text)
    if payload is None:
        logger.warning('program_generation_ai: resposta nao contem JSON valido.')
        return None, _ANTHROPIC_MODEL

    payload = _apply_deterministic_overrides(payload, plan_slug=plan_slug)

    errors = validate_payload(payload)
    if errors:
        logger.warning('program_generation_ai: payload gerado invalido: %s', '; '.join(errors))
        return None, _ANTHROPIC_MODEL

    return payload, _ANTHROPIC_MODEL


__all__ = ['generate_program_draft_payload']
