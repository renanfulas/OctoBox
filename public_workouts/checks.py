"""Checks de deploy do funil comercial Curva."""

from django.conf import settings
from django.core.checks import Error, Tags, register


@register(Tags.security, deploy=True)
def public_workout_commerce_configuration(app_configs, **kwargs):
    required = (
        'STRIPE_SECRET_KEY',
        'PUBLIC_WORKOUT_STRIPE_WEBHOOK_SECRET',
        'PUBLIC_WORKOUT_STRIPE_PRICE_ID_ESSENCIAL',
        'PUBLIC_WORKOUT_STRIPE_PRICE_ID_COMPLETO',
        'PUBLIC_WORKOUT_STRIPE_PRICE_ID_PREMIUM',
        'PUBLIC_WORKOUT_OFFER_VERSION',
        'PUBLIC_WORKOUT_SERVICE_POLICY_VERSION',
        'PUBLIC_WORKOUT_TERMS_VERSION',
        'PUBLIC_WORKOUT_PRIVACY_VERSION',
        'PUBLIC_WORKOUT_PUBLIC_BASE_URL',
    )
    errors = []
    for setting_name in required:
        if not str(getattr(settings, setting_name, '') or '').strip():
            errors.append(Error(
                f'{setting_name} nao esta configurado para o checkout Curva.',
                hint='Defina a variavel no ambiente de producao antes do deploy.',
                id=f'public_workouts.E{100 + len(errors)}',
            ))
    capacity_mode = str(getattr(settings, 'PUBLIC_WORKOUT_CAPACITY_MODE', '') or '')
    if capacity_mode not in {'observe', 'warn', 'enforce'}:
        errors.append(Error(
            'PUBLIC_WORKOUT_CAPACITY_MODE deve ser observe, warn ou enforce.',
            id='public_workouts.E120',
        ))
    threshold = float(getattr(settings, 'PUBLIC_WORKOUT_CAPACITY_MAX_UTILIZATION', 0) or 0)
    if not 0 < threshold <= 1:
        errors.append(Error(
            'PUBLIC_WORKOUT_CAPACITY_MAX_UTILIZATION deve estar entre 0 e 1.',
            id='public_workouts.E121',
        ))
    return errors
