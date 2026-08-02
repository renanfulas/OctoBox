"""
ARQUIVO: reconciliacao de origem comercial do aluno.

POR QUE ELE EXISTE:
- concentra a regra de resolucao entre origem operacional e origem declarada.
- impede que cada borda do sistema reconcilie o mesmo dado de um jeito diferente.
"""

from dataclasses import dataclass

from shared_support.acquisition import SENTINEL_ACQUISITION_CHANNELS, normalize_acquisition_channel


@dataclass(frozen=True, slots=True)
class AcquisitionResolution:
    resolved_acquisition_source: str
    resolved_source_detail: str
    source_confidence: str
    source_conflict_flag: bool
    source_resolution_method: str
    source_resolution_reason: str


def resolve_acquisition_resolution(
    *,
    operational_source: str = '',
    operational_detail: str = '',
    operational_method: str = '',
    declared_source: str = '',
    declared_detail: str = '',
) -> AcquisitionResolution:
    operational_source = normalize_acquisition_channel(operational_source)
    declared_source = normalize_acquisition_channel(declared_source)
    operational_detail = (operational_detail or '').strip()
    declared_detail = (declared_detail or '').strip()
    operational_method = (operational_method or '').strip()

    # Sentinela ('unidentified'/'legacy') nao e evidencia de canal em nenhum
    # dos dois lados — e' "nao sei" ou "veio de antes do contrato atual".
    # Zerar aqui, antes dos branches de conflito, evita conflito falso quando
    # um lado e sentinela e o outro tem uma origem real (ver auditoria de
    # leads 2026-07-28, achado M15). A branch antiga que tratava
    # operational_source == 'unidentified' como caso especial fica redundante
    # depois disso e foi removida: ela cai naturalmente em declared_only.
    if operational_source in SENTINEL_ACQUISITION_CHANNELS:
        operational_source = ''
        operational_detail = ''
    if declared_source in SENTINEL_ACQUISITION_CHANNELS:
        declared_source = ''
        declared_detail = ''

    if operational_source and declared_source and operational_source == declared_source:
        return AcquisitionResolution(
            resolved_acquisition_source=operational_source,
            resolved_source_detail=operational_detail or declared_detail,
            source_confidence='high',
            source_conflict_flag=False,
            source_resolution_method=operational_method or 'manual_form',
            source_resolution_reason='operational_declared_match',
        )

    if operational_source and declared_source:
        return AcquisitionResolution(
            resolved_acquisition_source=operational_source,
            resolved_source_detail=operational_detail,
            source_confidence='low',
            source_conflict_flag=True,
            source_resolution_method=operational_method or 'manual_review',
            source_resolution_reason='operational_declared_conflict',
        )

    if operational_source:
        return AcquisitionResolution(
            resolved_acquisition_source=operational_source,
            resolved_source_detail=operational_detail,
            source_confidence='high' if operational_method == 'intake_auto' else 'medium',
            source_conflict_flag=False,
            source_resolution_method=operational_method or 'manual_form',
            source_resolution_reason='operational_only',
        )

    if declared_source:
        return AcquisitionResolution(
            resolved_acquisition_source=declared_source,
            resolved_source_detail=declared_detail,
            source_confidence='medium',
            source_conflict_flag=False,
            source_resolution_method='declared_only',
            source_resolution_reason='declared_only',
        )

    return AcquisitionResolution(
        resolved_acquisition_source='',
        resolved_source_detail='',
        source_confidence='unknown',
        source_conflict_flag=False,
        source_resolution_method=operational_method,
        source_resolution_reason='',
    )


__all__ = ['AcquisitionResolution', 'resolve_acquisition_resolution']
