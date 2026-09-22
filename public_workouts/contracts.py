"""Contrato comercial versionado do Curva.

Os identificadores sao persistidos na assinatura no momento do checkout.
Mudar copy, termos ou policy exige uma nova versao; nunca altera
retroativamente o que um cliente aceitou.
"""

from django.conf import settings


DEFAULT_OFFER_VERSION = 'curva-2026-09-v1'
DEFAULT_SERVICE_POLICY_VERSION = 'curva-service-2026-09-v1'
DEFAULT_TERMS_VERSION = '2026-09-20'
DEFAULT_PRIVACY_VERSION = '2026-09-20'
REFUND_GUARANTEE_DAYS = 7


def current_contract_versions() -> dict[str, str]:
    return {
        'offer_version': str(
            getattr(settings, 'PUBLIC_WORKOUT_OFFER_VERSION', DEFAULT_OFFER_VERSION)
        ),
        'service_policy_version': str(
            getattr(
                settings,
                'PUBLIC_WORKOUT_SERVICE_POLICY_VERSION',
                DEFAULT_SERVICE_POLICY_VERSION,
            )
        ),
        'terms_version': str(
            getattr(settings, 'PUBLIC_WORKOUT_TERMS_VERSION', DEFAULT_TERMS_VERSION)
        ),
        'privacy_version': str(
            getattr(settings, 'PUBLIC_WORKOUT_PRIVACY_VERSION', DEFAULT_PRIVACY_VERSION)
        ),
    }


__all__ = [
    'REFUND_GUARANTEE_DAYS',
    'current_contract_versions',
]
