"""
ARQUIVO: calculo puro do feature layer de leads (Onda 6).

POR QUE ELE EXISTE:
- separa a conta (deterministica, testavel sem banco) da orquestracao
  (busca de dados + persistencia, em intelligence/leads/jobs.py). Nada
  aqui abre conexao com banco.

O QUE ESTE ARQUIVO FAZ:
1. deduplica linhas por phone_lookup_index (unica chave de join valida —
   phone e EncryptedCharField, nao serve para dedupe; ver achado L3 da
   auditoria de leads).
2. resolve canal + procedencia por linha (reusa a leitura da Onda 3/5).
3. agrega por (canal, procedencia): capturado/convertido/rejeitado/aberto
   e mediana de dias ate conversao.
4. expoe o piso de publicacao de taxa (suprime, nao zera, celula pequena).

PONTOS CRITICOS:
- so emite celula para (canal, procedencia) com captured_total > 0 — tabela
  esparsa, nao uma grade combinatoria de canais x procedencias vazias.
- ML nunca escreve verdade primaria: esta funcao so LE dados ja buscados e
  calcula: nunca grava em StudentIntake/Student.
"""

from __future__ import annotations

import statistics
from datetime import datetime

from onboarding.attribution import extract_acquisition_channel_reading
from onboarding.models import IntakeStatus

DEFAULT_MIN_CONVERSIONS_TO_PUBLISH = 20


def _as_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    return value


def deduplicate_by_phone(rows):
    """Mantem so a linha mais antiga por phone_lookup_index — a captura
    original, nao reenvios do mesmo contato. Linha sem phone_lookup_index
    (nao deveria acontecer, mas e defensivo) passa direto sem dedupe."""
    earliest_by_phone = {}
    passthrough = []
    for row in rows:
        phone_lookup_index = row.get('phone_lookup_index')
        if not phone_lookup_index:
            passthrough.append(row)
            continue
        current = earliest_by_phone.get(phone_lookup_index)
        if current is None or row['created_at'] < current['created_at']:
            earliest_by_phone[phone_lookup_index] = row
    return list(earliest_by_phone.values()) + passthrough


def compute_lead_channel_facts(*, rows, rule_version, input_window, window_start, window_end, computed_at):
    """rows: iteravel de dicts com phone_lookup_index, created_at, status,
    converted_at, source, raw_payload — ja filtrados pela janela de
    maturacao pelo chamador (ver intelligence/leads/jobs.py).

    Retorna lista de dicts prontos para upsert em LeadChannelDailyFact.
    """
    deduped_rows = deduplicate_by_phone(rows)

    cells = {}
    for row in deduped_rows:
        reading = extract_acquisition_channel_reading(
            raw_payload=row.get('raw_payload'), fallback_source=row.get('source', '')
        )
        cell_key = (reading.channel, reading.provenance)
        cell = cells.setdefault(
            cell_key,
            {'captured_total': 0, 'converted_total': 0, 'rejected_total': 0, 'open_total': 0, 'conversion_days': []},
        )
        cell['captured_total'] += 1
        status = row.get('status')
        if status == IntakeStatus.APPROVED:
            cell['converted_total'] += 1
            created_date = _as_date(row.get('created_at'))
            converted_date = _as_date(row.get('converted_at'))
            if created_date is not None and converted_date is not None:
                cell['conversion_days'].append((converted_date - created_date).days)
        elif status == IntakeStatus.REJECTED:
            cell['rejected_total'] += 1
        else:
            cell['open_total'] += 1

    facts = []
    for (channel, provenance), totals in cells.items():
        conversion_days = totals.pop('conversion_days')
        median_days = round(statistics.median(conversion_days), 1) if conversion_days else None
        facts.append(
            {
                'window_start': window_start,
                'window_end': window_end,
                'channel': channel,
                'provenance': provenance,
                'median_days_to_conversion': median_days,
                'rule_version': rule_version,
                'computed_at': computed_at,
                'input_window': input_window,
                **totals,
            }
        )
    return facts


def resolve_publishable_conversion_rate(*, captured_total, converted_total, min_conversions_to_publish=DEFAULT_MIN_CONVERSIONS_TO_PUBLISH):
    """Piso de publicacao: celula com menos de min_conversions_to_publish
    conversoes NAO publica percentual (suprime, nao zera) — amostra pequena
    demais para virar leitura estatistica confiavel. Retorna None quando
    suprimido; o N continua disponivel separadamente para quem exibir isto.
    """
    if captured_total <= 0 or converted_total < min_conversions_to_publish:
        return None
    return round((converted_total / captured_total) * 100, 1)


__all__ = [
    'DEFAULT_MIN_CONVERSIONS_TO_PUBLISH',
    'compute_lead_channel_facts',
    'deduplicate_by_phone',
    'resolve_publishable_conversion_rate',
]
