"""Telemetria de atraso da sincronização offline do app Curva (F3,
docs/plans/curva-offline-first-estrategia.md).

O app grava no aparelho o que o aluno registra sem internet e envia depois;
cada envio drenado de uma fila traz `X-Curva-Queued-Ms` (quanto tempo esperou,
medido pelo relógio do próprio aparelho). Aqui vira uma linha de log
estruturada — tipo, faixa e segundos, sem conta, slug ou valor registrado —
para responder "quanto tempo os registros ficam presos nas academias sem
sinal" sem tabela nova.
"""

from __future__ import annotations

import logging

logger = logging.getLogger('octobox.curva.offline')

QUEUED_HEADER = 'HTTP_X_CURVA_QUEUED_MS'
# Abaixo disso é envio normal (write-ahead online), não atraso.
MIN_LAG_MS = 60_000
# Acima disso o número não é confiável (relógio mexido, valor forjado).
MAX_LAG_MS = 90 * 86_400_000

_BUCKETS = (
    (5 * 60_000, 'lt_5m'),
    (60 * 60_000, 'lt_1h'),
    (24 * 60 * 60_000, 'lt_1d'),
    (7 * 24 * 60 * 60_000, 'lt_7d'),
)


def offline_sync_lag_ms(request) -> int | None:
    raw = request.META.get(QUEUED_HEADER, '')
    if not raw.isdigit():
        return None
    value = int(raw)
    if value < MIN_LAG_MS or value > MAX_LAG_MS:
        return None
    return value


def lag_bucket(lag_ms: int) -> str:
    for limit, label in _BUCKETS:
        if lag_ms < limit:
            return label
    return 'gte_7d'


def log_offline_sync_lag(request, kind: str) -> None:
    lag_ms = offline_sync_lag_ms(request)
    if lag_ms is None:
        return
    logger.info(
        'curva_offline_sync_lag kind=%s bucket=%s lag_s=%d',
        kind, lag_bucket(lag_ms), lag_ms // 1000,
    )
