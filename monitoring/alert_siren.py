"""
ARQUIVO: engine minima da Alert Siren.

POR QUE ELE EXISTE:
- consolida risco confiavel e devolve postura defensiva pequena, objetiva e reversivel.
- prepara a evolucao da sirene sem inventar um sistema paralelo ao Beacon.
"""

from monitoring.defense_actions import (
    build_alert_siren_actions,
    build_alert_siren_defense_policy,
)
from monitoring.risk_states import (
    ALERT_SIREN_LEVEL_HIGH,
    ALERT_SIREN_LEVEL_LOW,
    ALERT_SIREN_LEVEL_MEDIUM,
    ALERT_SIREN_LEVEL_SILENT,
    build_signal_mesh_risk_state,
)


def _build_headline(level: str) -> str:
    headlines = {
        ALERT_SIREN_LEVEL_SILENT: 'Alert Siren silenciosa',
        ALERT_SIREN_LEVEL_LOW: 'Alert Siren em observacao reforcada',
        ALERT_SIREN_LEVEL_MEDIUM: 'Alert Siren em degradacao controlada',
        ALERT_SIREN_LEVEL_HIGH: 'Alert Siren em contencao defensiva',
    }
    return headlines[level]


def _build_summary(*, level: str, signal_mesh_snapshot: dict) -> str:
    total_due_backlog = signal_mesh_snapshot.get('total_due_backlog', 0)
    if level == ALERT_SIREN_LEVEL_HIGH:
        return (
            f'O backlog e os skips ja passaram do ponto de conforto. A malha reduz vazao e segura webhooks ate o corredor respirar.'
        )
    if level == ALERT_SIREN_LEVEL_MEDIUM:
        return (
            f'Ha pressao operacional suficiente para desacelerar retries e priorizar estabilidade antes de ampliar throughput.'
        )
    if level == ALERT_SIREN_LEVEL_LOW:
        return (
            f'Existe pressao leve na malha com {total_due_backlog} item(ns) vencido(s). Ainda e observacao, nao crise.'
        )
    return 'Sem risco consolidado relevante agora. A malha opera em baseline seguro.'


def build_alert_siren_snapshot(*, signal_mesh_snapshot: dict | None = None) -> dict:
    snapshot = signal_mesh_snapshot
    if snapshot is None:
        from monitoring.beacon_snapshot import build_signal_mesh_beacon_snapshot

        snapshot = build_signal_mesh_beacon_snapshot()

    risk_state = build_signal_mesh_risk_state(snapshot)
    level = risk_state['level']
    defense_policy = build_alert_siren_defense_policy(level=level)
    return {
        'label': 'Alert Siren',
        'level': level,
        'tone': risk_state['tone'],
        'headline': _build_headline(level),
        'summary': _build_summary(level=level, signal_mesh_snapshot=snapshot),
        'risk_state': risk_state,
        'actions': build_alert_siren_actions(level=level, signal_mesh_snapshot=snapshot),
        'defense_policy': defense_policy,
    }


def get_alert_siren_defense_policy(*, signal_mesh_snapshot: dict | None = None) -> dict:
    snapshot = build_alert_siren_snapshot(signal_mesh_snapshot=signal_mesh_snapshot)
    return snapshot['defense_policy']


__all__ = [
    'build_alert_siren_snapshot',
    'get_alert_siren_defense_policy',
]
