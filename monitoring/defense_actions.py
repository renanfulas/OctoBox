"""
ARQUIVO: politicas defensivas minimas da Alert Siren.

POR QUE ELE EXISTE:
- liga cada nivel da sirene a mudancas pequenas, reversiveis e reais.
- evita que a sirene vire texto bonito sem efeito no corredor da malha.
"""

from django.conf import settings

from monitoring.risk_states import (
    ALERT_SIREN_LEVEL_HIGH,
    ALERT_SIREN_LEVEL_LOW,
    ALERT_SIREN_LEVEL_MEDIUM,
    ALERT_SIREN_LEVEL_SILENT,
)


def build_alert_siren_defense_policy(*, level: str) -> dict:
    if level == ALERT_SIREN_LEVEL_HIGH:
        return {
            'level': level,
            'job_limit_cap': getattr(settings, 'ALERT_SIREN_HIGH_JOB_LIMIT_CAP', 5),
            'webhook_limit_cap': getattr(settings, 'ALERT_SIREN_HIGH_WEBHOOK_LIMIT_CAP', 0),
            'pause_webhook_retries': True,
            'pause_non_essential_job_submissions': True,
        }

    if level == ALERT_SIREN_LEVEL_MEDIUM:
        return {
            'level': level,
            'job_limit_cap': getattr(settings, 'ALERT_SIREN_MEDIUM_JOB_LIMIT_CAP', 10),
            'webhook_limit_cap': getattr(settings, 'ALERT_SIREN_MEDIUM_WEBHOOK_LIMIT_CAP', 10),
            'pause_webhook_retries': False,
            'pause_non_essential_job_submissions': False,
        }

    return {
        'level': level,
        'job_limit_cap': None,
        'webhook_limit_cap': None,
        'pause_webhook_retries': False,
        'pause_non_essential_job_submissions': False,
    }


def build_alert_siren_actions(*, level: str, signal_mesh_snapshot: dict | None) -> list[dict]:
    total_due_backlog = (signal_mesh_snapshot or {}).get('total_due_backlog', 0)
    if level == ALERT_SIREN_LEVEL_HIGH:
        return [
            {
                'action': 'contain-webhook-retries',
                'label': 'Conter retries de webhook',
                'summary': 'Webhooks vencidos entram em contenção para proteger o núcleo enquanto o corredor estabiliza.',
            },
            {
                'action': 'pause-non-essential-imports',
                'label': 'Congelar imports não essenciais',
                'summary': 'Novos imports assíncronos esperam o corredor estabilizar antes de ganhar mais pressão.',
            },
            {
                'action': 'cap-job-retries',
                'label': 'Reduzir vazão de retries de jobs',
                'summary': 'Jobs vencidos continuam fluindo, mas em vazão reduzida para evitar avalanche.',
            },
        ]

    if level == ALERT_SIREN_LEVEL_MEDIUM:
        return [
            {
                'action': 'cap-retry-sweeps',
                'label': 'Segurar a vazão do sweep',
                'summary': 'A malha continua reprocessando, mas com limite menor para ganhar controle da fila.',
            },
            {
                'action': 'observe-skips',
                'label': 'Acompanhar skips com lupa',
                'summary': 'Os motivos ignorados viram foco de saneamento antes de ampliarem o backlog.',
            },
        ]

    if level == ALERT_SIREN_LEVEL_LOW:
        return [
            {
                'action': 'watch-backlog',
                'label': 'Observar backlog de perto',
                'summary': (
                    f'Ha {total_due_backlog} item(ns) vencido(s). Ainda nao e contenção, mas ja pede vigia reforçada.'
                ),
            },
        ]

    return [
        {
            'action': 'baseline',
            'label': 'Operar em baseline seguro',
            'summary': 'Sem backlog vencido relevante agora. O corredor da malha segue em ritmo normal.',
        },
    ]


__all__ = [
    'build_alert_siren_actions',
    'build_alert_siren_defense_policy',
]
