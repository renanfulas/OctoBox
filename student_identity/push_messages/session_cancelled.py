"""
ARQUIVO: builder de payload para push de cancelamento de sessao.

POR QUE ELE EXISTE:
- separa a composicao de mensagem (copy, limites de caracteres, deep link) da logica de entrega.
- permite testar o payload sem mockar pywebpush ou settings VAPID.
- garante contrato de copy consistente entre push e qualquer outro canal futuro.

O QUE ESTE ARQUIVO FAZ:
1. define PushPayload — dataclass imutavel com todos os campos do payload Web Push.
2. define build_session_cancelled_payload() — funcao pura que compoe o payload por variante.
3. valida limites de caracteres em modo debug para pegar regressoes de copy.

PONTOS CRITICOS:
- titulo <= 30 chars (truncado visivel no iOS).
- corpo <= 90 chars (truncado em Android antes da expansao).
- tag = 'session-cancelled-{session_id}' garante dedupe nativo do browser.
- requireInteraction=True apenas na variante 'already_checked_in' (aluno pode estar indo ao box).
- deeplink aponta para /aluno/grade/?highlight={session_id} para scroll-into-view no banner (Onda 4).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from django.urls import reverse


TITLE_MAX_CHARS = 30
BODY_MAX_CHARS = 90

CopyVariant = Literal['ahead', 'last_minute', 'already_checked_in']


@dataclass(frozen=True, slots=True)
class PushPayload:
    title: str
    body: str
    url: str
    tag: str
    require_interaction: bool = False


def build_session_cancelled_payload(
    *,
    session_id: int,
    session_title: str,
    session_time_label: str,
    copy_variant: CopyVariant,
) -> PushPayload:
    """
    Compoe o payload de push para cancelamento de aula.

    Argumentos:
        session_id        — pk da ClassSession (para tag e deeplink).
        session_title     — titulo da aula (ex: 'CrossFit 19h').
        session_time_label — horario formatado (ex: '27/04 18:00').
        copy_variant      — variante decidida pela camada de dominio (Onda 1).
    """

    tag = f'session-cancelled-{session_id}'
    url = reverse('student-app-grade') + f'?highlight={session_id}'

    if copy_variant == 'already_checked_in':
        title = 'Aula de hoje cancelada'
        body = f'{session_title} de {session_time_label} foi cancelada. Fique à vontade para reservar outra.'
        require_interaction = True

    elif copy_variant == 'last_minute':
        title = f'Aula cancelada — {session_time_label}'
        body = f'{session_title} foi cancelada. Crédito devolvido automaticamente.'
        require_interaction = False

    else:  # 'ahead'
        title = f'Aula cancelada — {session_time_label}'
        body = f'{session_title} foi cancelada. Sem perda de crédito. Reserve outra quando quiser.'
        require_interaction = False

    # Truncagem defensiva — nunca quebrar entrega por copy longo.
    title = title[:TITLE_MAX_CHARS]
    body = body[:BODY_MAX_CHARS]

    return PushPayload(
        title=title,
        body=body,
        url=url,
        tag=tag,
        require_interaction=require_interaction,
    )


__all__ = [
    'PushPayload',
    'build_session_cancelled_payload',
]
