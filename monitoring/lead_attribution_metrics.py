"""
Metricas operacionais do funil de atribuicao comercial.

POR QUE ELE EXISTE:
- separa observabilidade de qualidade de origem do restante das metricas HTTP.
- prepara instrumentos simples para acompanhar cobertura de dados antes do ML.
"""

from prometheus_client import Counter


LEAD_ATTRIBUTION_CAPTURE_TOTAL = Counter(
    'octobox_lead_attribution_capture_total',
    'Total de capturas de atribuicao comercial no intake.',
    ['entry_kind', 'operational_source', 'acquisition_channel'],
)

LEAD_ATTRIBUTION_QUALIFICATION_TOTAL = Counter(
    'octobox_lead_attribution_qualification_total',
    'Total de qualificacoes complementares de origem comercial.',
    ['response_channel', 'confirmed_channel'],
)


def record_lead_attribution_capture(*, entry_kind: str, operational_source: str, acquisition_channel: str) -> None:
    LEAD_ATTRIBUTION_CAPTURE_TOTAL.labels(
        entry_kind=str(entry_kind or '').strip().lower() or 'unknown',
        operational_source=str(operational_source or '').strip().lower() or 'unknown',
        acquisition_channel=str(acquisition_channel or '').strip().lower() or 'missing',
    ).inc()


def record_lead_attribution_qualification(*, response_channel: str, confirmed_channel: str) -> None:
    LEAD_ATTRIBUTION_QUALIFICATION_TOTAL.labels(
        response_channel=str(response_channel or '').strip().lower() or 'unknown',
        confirmed_channel=str(confirmed_channel or '').strip().lower() or 'missing',
    ).inc()


__all__ = [
    'record_lead_attribution_capture',
    'record_lead_attribution_qualification',
]
