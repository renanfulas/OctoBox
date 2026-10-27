"""
ARQUIVO: helpers de teste para entrar no Curva como dono do slug.

POR QUE ELE EXISTE:
- `/renan/<slug>` exige sessao de login verificada; abrir o link sem login
  manda para `/treinos/login`. Testes de pagina precisam do mesmo caminho
  que o aluno real: conta + assinatura + cookie verificado.
"""

from __future__ import annotations

from public_workouts.models import PublicWorkoutAccount, PublicWorkoutSubscription
from student_identity.public_workout_session import (
    PUBLIC_WORKOUT_SESSION_COOKIE_NAME,
    build_public_workout_session_value,
)


def sign_in_public_workout_account(client, account: PublicWorkoutAccount) -> PublicWorkoutAccount:
    client.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = build_public_workout_session_value(
        account_id=account.pk, identity_verified=True,
    )
    return account


def sign_in_public_workout_owner(client, plan_slug: str, *, email: str | None = None, **subscription_fields):
    account = PublicWorkoutAccount.objects.create(email=email or f'{plan_slug}-dono@example.com')
    PublicWorkoutSubscription.objects.create(account=account, plan_slug=plan_slug, **subscription_fields)
    return sign_in_public_workout_account(client, account)


def publish_example_program(plan_slug: str):
    """Programa de exemplo ativo para `plan_slug` (sem ele /renan/<slug> leva a Minha conta)."""
    from public_workouts.schema import build_example_payload
    from public_workouts.services import publish_program

    payload = build_example_payload()
    payload['program_id'] = f'{plan_slug}-exemplo'
    return publish_program(slug=plan_slug, payload=payload)
