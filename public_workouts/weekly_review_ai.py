"""
ARQUIVO: geracao de texto de revisao semanal via LLM (Claude Haiku).

POR QUE ELE EXISTE:
- `build_weekly_review` (services.py) so calcula os SINAIS deterministicos
  (tendencia de 1RM por movimento) — a propria docstring dele e o teste
  estatico `test_never_calls_an_ai_provider` (test_weekly_review.py)
  proibem qualquer import de IA dentro de services.py. Este modulo e onde
  a chamada de IA de verdade mora, separado de proposito, pra nunca violar
  essa fronteira.

O QUE ESTE ARQUIVO FAZ:
1. recebe o dict que `build_weekly_review` ja calculou (nunca consulta o
   banco aqui).
2. chama a Anthropic (Claude Haiku) com esses sinais, pede 2-3 frases em
   PT-BR de revisao.
3. falha graciosamente (retorna `None`, nunca levanta excecao) sem chave
   configurada, sem sinal nenhum pra comentar, timeout, erro HTTP ou
   resposta vazia — a tela de revisao semanal nunca quebra por causa da IA.

PONTOS CRITICOS:
- Mesmo padrao de `operations/services/wod_session_llm_parser.py` (o unico
  precedente real de chamada a LLM no projeto): HTTP cru via `requests`,
  NAO o SDK `anthropic` — evita dependencia nova so pra isto.
- Timeout curto (10s): quem clica em "gerar revisao" esta esperando na
  tela, nao pode travar.
- `ANTHROPIC_API_KEY` via `os.getenv` direto (nao Django settings) — mesma
  convencao do `wod_session_llm_parser.py`.
- O prompt pede explicitamente pra nunca inventar numero fora do dict
  recebido — sinais ja vem calculados, o texto so precisa descrever.
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
    'Voce e um personal trainer revisando o treino de um aluno, uma vez por '
    'semana. Voce recebe SO sinais ja calculados (tendencia de 1RM por '
    'movimento, nunca a tabela de sets crua) — nunca invente numero que nao '
    'esteja nos dados recebidos.\n\n'
    'Responda em portugues do Brasil, 2 a 3 frases, tom direto e '
    'encorajador (nao robotico, nao generico). Cite os movimentos pelo '
    'nome do slug recebido. Se nao houver nenhum movimento em queda ou '
    'plato, comente a evolucao geral de forma breve, sem elogio vazio.'
)


def generate_weekly_review_text(review: dict) -> str | None:
    """Transforma o dict de `build_weekly_review` em texto curto de revisao.

    `review` e exatamente o retorno de
    `public_workouts.services.build_weekly_review` — este modulo nunca
    consulta o banco, so formata o que ja veio calculado.

    Retorna `None` (nunca levanta excecao) sem `ANTHROPIC_API_KEY`
    configurada, sem `trends_by_movement` pra comentar, timeout, erro HTTP
    ou resposta vazia — sempre ha um fallback neutro pra esses casos.
    """
    trends = review.get('trends_by_movement') or {}
    if not trends:
        return None

    api_key = os.getenv('ANTHROPIC_API_KEY', '').strip()
    if not api_key:
        logger.debug('weekly_review_ai: ANTHROPIC_API_KEY nao configurada.')
        return None

    user_message = (
        f'Sinais desta semana: {trends}\n'
        f"Movimentos em queda: {review.get('declining_movements') or []}\n"
        f"Movimentos em plato: {review.get('plateaued_movements') or []}"
    )

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
                'max_tokens': 256,
                'system': _SYSTEM_PROMPT,
                'messages': [{'role': 'user', 'content': user_message}],
            },
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        logger.warning('weekly_review_ai: chamada a Anthropic falhou: %s', exc)
        return None

    parts = [block.get('text', '') for block in data.get('content', []) if block.get('type') == 'text']
    text = '\n'.join(parts).strip()
    return text or None


__all__ = ['generate_weekly_review_text']
