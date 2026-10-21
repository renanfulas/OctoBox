"""
ARQUIVO: estado assinado do login por Google do corredor de treinos.

POR QUE ELE EXISTE:
- Onda B1 do CORDA (docs/plans/public-workouts-produtizacao-corda.md):
  "aluno entra com Google" era o unico item do "pronto quando" que ainda
  faltava (o login por e-mail — public_workout_login.py — ja cobria o
  resto). Google reusa GoogleOAuthProvider (oauth_providers.py) como
  SERVICO stateless (fala com a API do Google, devolve e-mail) — nunca o
  StudentOAuthCallbackView nem a StudentIdentity do /aluno/, que sao de
  outro produto (fluxo de convite de box).

PONTOS CRITICOS:
- O `state` viaja assinado (django.core.signing), nunca em request.session
  — mesmo padrao de oauth_state.py (StudentIdentity), so que carrega
  `next_url` (destino dentro do corredor) em vez de `invite_token`
  (semantica de convite de box, que nao existe aqui).
- Resolver a PublicWorkoutAccount pelo e-mail do Google e feito por
  resolve_or_create_public_workout_account (public_workout_login.py) —
  o mesmo helper que o login por e-mail ja usa. Um so lugar decide o que
  "achar ou criar conta por e-mail" significa pro corredor.
"""

from __future__ import annotations

from django.core import signing

PUBLIC_WORKOUT_OAUTH_STATE_SALT = 'student_identity.public_workout_oauth_state'
PUBLIC_WORKOUT_OAUTH_STATE_MAX_AGE_SECONDS = 600


def build_public_workout_oauth_state(*, next_url: str = '') -> str:
    return signing.dumps(
        {'next_url': (next_url or '').strip()},
        salt=PUBLIC_WORKOUT_OAUTH_STATE_SALT,
        compress=True,
    )


def read_public_workout_oauth_state(raw_state: str) -> dict | None:
    if not raw_state:
        return None
    try:
        return signing.loads(
            raw_state,
            salt=PUBLIC_WORKOUT_OAUTH_STATE_SALT,
            max_age=PUBLIC_WORKOUT_OAUTH_STATE_MAX_AGE_SECONDS,
        )
    except signing.BadSignature:
        return None
