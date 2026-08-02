"""
Contrato estruturado de atribuicao e qualificacao do funil de intake.

POR QUE ELE EXISTE:
- separa a origem operacional do registro da origem comercial declarada.
- prepara um formato estavel para analytics, qualificacao posterior e ML.

O QUE ESTE ARQUIVO FAZ:
1. define choices de canal de captacao em baixa cardinalidade.
2. monta payload estruturado para salvar em raw_payload do intake.
3. le a origem comercial a partir do payload com fallback legado.
4. prepara merge futuro de resposta complementar via formularios externos.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import Any

LEGACY_SOURCE_TO_ACQUISITION_CHANNEL = {
    'csv': 'referral',
    'whatsapp': 'whatsapp',
}
# v2 (2026-07-29): captured_at passa a ser preenchido de verdade no quick
# create (antes ficava sempre null); ver auditoria de leads, achado M3.
ATTRIBUTION_SCHEMA_VERSION = 2

from shared_support.acquisition import (
    ACQUISITION_CHANNEL_CHOICES,
    ACQUISITION_CHANNEL_LABELS,
    get_acquisition_channel_label,
    normalize_acquisition_channel,
)


def build_intake_attribution_payload(
    *,
    source: str,
    acquisition_channel: str = '',
    acquisition_detail: str = '',
    entry_kind: str = '',
    actor_id: int | None = None,
    captured_via: str = 'intake-center',
    captured_at: datetime | None = None,
) -> dict[str, Any]:
    normalized_channel = normalize_acquisition_channel(acquisition_channel)
    detail = str(acquisition_detail or '').strip()
    captured_timestamp = (captured_at.isoformat() if captured_at is not None else None)
    return {
        'entry_kind': str(entry_kind or '').strip().lower(),
        'attribution': {
            'schema_version': ATTRIBUTION_SCHEMA_VERSION,
            'operational_source': str(source or '').strip().lower(),
            'captured_via': str(captured_via or '').strip() or 'intake-center',
            'captured_at': captured_timestamp,
            'captured_by_actor_id': actor_id,
            'acquisition': {
                'declared_channel': normalized_channel,
                'declared_detail': detail,
                'is_declared': bool(normalized_channel),
            },
            'qualification': {
                'status': 'pending',
                'confirmed_channel': '',
                'confirmed_detail': '',
                'response_channel': '',
                'respondent_kind': '',
                'responded_at': None,
            },
            'ml_features': {
                'has_declared_channel': bool(normalized_channel),
                'has_declared_detail': bool(detail),
                'needs_additional_qualification': not bool(normalized_channel),
            },
        },
    }


def merge_qualification_response(
    *,
    raw_payload: dict[str, Any] | None,
    confirmed_channel: str = '',
    confirmed_detail: str = '',
    response_channel: str = 'google_forms',
    respondent_kind: str = 'student',
    responded_at: datetime | None = None,
) -> dict[str, Any]:
    payload = deepcopy(raw_payload or {})
    attribution = payload.setdefault('attribution', {})
    attribution.setdefault('schema_version', ATTRIBUTION_SCHEMA_VERSION)
    attribution.setdefault('operational_source', '')
    attribution.setdefault('captured_via', '')
    attribution.setdefault('captured_at', None)
    attribution.setdefault('captured_by_actor_id', None)
    acquisition = attribution.setdefault('acquisition', {})
    acquisition.setdefault('declared_channel', '')
    acquisition.setdefault('declared_detail', '')
    acquisition.setdefault('is_declared', bool(acquisition.get('declared_channel')))
    qualification = attribution.setdefault('qualification', {})

    normalized_channel = normalize_acquisition_channel(confirmed_channel)
    detail = str(confirmed_detail or '').strip()
    qualification.update(
        {
            'status': 'confirmed' if normalized_channel else 'pending',
            'confirmed_channel': normalized_channel,
            'confirmed_detail': detail,
            'response_channel': str(response_channel or '').strip().lower(),
            'respondent_kind': str(respondent_kind or '').strip().lower(),
            'responded_at': responded_at.isoformat() if responded_at is not None else None,
        }
    )

    ml_features = attribution.setdefault('ml_features', {})
    ml_features.update(
        {
            'has_declared_channel': bool(acquisition.get('declared_channel')),
            'has_declared_detail': bool(acquisition.get('declared_detail')),
            'has_confirmed_channel': bool(normalized_channel),
            'needs_additional_qualification': not bool(normalized_channel),
        }
    )
    return payload


@dataclass(frozen=True, slots=True)
class AcquisitionChannelReading:
    channel: str
    provenance: str  # 'confirmed' | 'declared' | 'legacy_inferred' | 'missing'


def extract_acquisition_channel_reading(
    *, raw_payload: dict[str, Any] | None, fallback_source: str = ''
) -> AcquisitionChannelReading:
    payload = raw_payload or {}
    attribution = payload.get('attribution') if isinstance(payload, dict) else {}
    if isinstance(attribution, dict):
        qualification = attribution.get('qualification') or {}
        if isinstance(qualification, dict):
            confirmed_channel = normalize_acquisition_channel(qualification.get('confirmed_channel'))
            if confirmed_channel:
                return AcquisitionChannelReading(channel=confirmed_channel, provenance='confirmed')

        acquisition = attribution.get('acquisition') or {}
        if isinstance(acquisition, dict):
            declared_channel = normalize_acquisition_channel(acquisition.get('declared_channel'))
            if declared_channel:
                return AcquisitionChannelReading(channel=declared_channel, provenance='declared')

    legacy_channel = LEGACY_SOURCE_TO_ACQUISITION_CHANNEL.get(str(fallback_source or '').strip().lower(), '')
    if legacy_channel:
        return AcquisitionChannelReading(channel=legacy_channel, provenance='legacy_inferred')

    return AcquisitionChannelReading(channel='', provenance='missing')


def extract_acquisition_channel(*, raw_payload: dict[str, Any] | None, fallback_source: str = '') -> str:
    return extract_acquisition_channel_reading(raw_payload=raw_payload, fallback_source=fallback_source).channel


def summarize_acquisition_channels(rows: list[tuple[str, dict[str, Any] | None]]) -> dict[str, int]:
    """Conta leads por canal.

    PONTOS CRITICOS:
    - canal 'legacy_inferred' (inferido de um source legado, ex: CSV -> referral)
      NAO entra na contagem do canal real: e inferencia, nao declaracao. Ele soma
      em 'legacy_inferred', um balde proprio, para nao inflar 'referral' com
      registros que ninguem de fato declarou (ver auditoria de leads, achado M6).
    """
    counts = {key: 0 for key in ACQUISITION_CHANNEL_LABELS}
    missing_total = 0
    legacy_inferred_total = 0
    for source, raw_payload in rows:
        reading = extract_acquisition_channel_reading(raw_payload=raw_payload, fallback_source=source)
        if reading.provenance == 'missing':
            missing_total += 1
        elif reading.provenance == 'legacy_inferred':
            legacy_inferred_total += 1
        else:
            counts[reading.channel] += 1
    counts['missing'] = missing_total
    counts['legacy_inferred'] = legacy_inferred_total
    return counts


__all__ = [
    'ACQUISITION_CHANNEL_CHOICES',
    'ACQUISITION_CHANNEL_LABELS',
    'ATTRIBUTION_SCHEMA_VERSION',
    'AcquisitionChannelReading',
    'build_intake_attribution_payload',
    'extract_acquisition_channel',
    'extract_acquisition_channel_reading',
    'get_acquisition_channel_label',
    'merge_qualification_response',
    'normalize_acquisition_channel',
    'summarize_acquisition_channels',
]
