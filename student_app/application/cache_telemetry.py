"""
ARQUIVO: telemetria leve de cache do app do aluno.

POR QUE ELE EXISTE:
- Publica hit/miss e duracao dos snapshots do app do aluno no request atual.

O QUE ESTE ARQUIVO FAZ:
1. Registra metricas compactas no dicionario `_octobox_request_perf`.
2. Mantem contrato pequeno para o middleware emitir `Server-Timing`.

PONTOS CRITICOS:
- A telemetria precisa ser opcional e sem custo relevante quando ausente.
- O collector nao deve disparar banco nem cache extra por conta propria.
"""

from __future__ import annotations


def record_student_app_perf(request_perf, key: str, *, total_ms: float, cache_lookup_ms: float, build_ms: float, cache_hit: bool):
    if not isinstance(request_perf, dict):
        return
    student_perf = request_perf.setdefault('student_app', {})
    student_perf[key] = {
        'total_ms': round(total_ms, 2),
        'cache_lookup_ms': round(cache_lookup_ms, 2),
        'build_ms': round(build_ms, 2),
        'cache_hit': bool(cache_hit),
    }


__all__ = ['record_student_app_perf']
