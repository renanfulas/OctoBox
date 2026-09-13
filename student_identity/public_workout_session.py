"""
ARQUIVO: cookie de sessao do corredor de treinos (/treinos/).

POR QUE ELE EXISTE:
- S2 do CORDA (docs/plans/public-workouts-produtizacao-corda.md, Onda B1):
  cookie proprio, nome/path/validade independentes do cookie do aluno de
  box (student_identity/infrastructure/session.py). Molde copiado de la
  (D.00) — stateless, assinado, 1 variavel — mas sem nocao de box: o
  corredor nao tem tenant.
"""

from __future__ import annotations

from django.conf import settings
from django.core import signing

PUBLIC_WORKOUT_SESSION_SALT = 'student_identity.public_workout_session'
PUBLIC_WORKOUT_SESSION_COOKIE_NAME = 'octobox_treinos_session'
PUBLIC_WORKOUT_SESSION_PATH = '/treinos/'


def get_public_workout_session_max_age() -> int:
    return int(getattr(settings, 'PUBLIC_WORKOUT_SESSION_COOKIE_AGE', 2592000))


def build_public_workout_session_value(*, account_id: int) -> str:
    return signing.dumps({'account_id': int(account_id)}, salt=PUBLIC_WORKOUT_SESSION_SALT, compress=True)


def read_public_workout_session_value(raw_value: str | None) -> dict | None:
    if not raw_value:
        return None
    try:
        return signing.loads(
            raw_value,
            salt=PUBLIC_WORKOUT_SESSION_SALT,
            max_age=get_public_workout_session_max_age(),
        )
    except signing.BadSignature:
        return None


def attach_public_workout_session_cookie(response, *, account_id: int):
    response.set_cookie(
        PUBLIC_WORKOUT_SESSION_COOKIE_NAME,
        build_public_workout_session_value(account_id=account_id),
        max_age=get_public_workout_session_max_age(),
        httponly=True,
        secure=bool(getattr(settings, 'SESSION_COOKIE_SECURE', False)),
        samesite='Lax',
        path=PUBLIC_WORKOUT_SESSION_PATH,
    )
    return response


def clear_public_workout_session_cookie(response):
    response.delete_cookie(PUBLIC_WORKOUT_SESSION_COOKIE_NAME, path=PUBLIC_WORKOUT_SESSION_PATH, samesite='Lax')
    return response


def get_public_workout_account_id_from_request(request) -> int | None:
    """Le o cookie da requisicao e devolve o account_id, ou None se ausente/invalido.

    So decodifica a assinatura — nao consulta o banco (quem chama decide se
    precisa carregar a PublicWorkoutAccount ou so precisa do id).
    """
    raw_value = request.COOKIES.get(PUBLIC_WORKOUT_SESSION_COOKIE_NAME)
    data = read_public_workout_session_value(raw_value)
    if not data:
        return None
    account_id = data.get('account_id')
    return int(account_id) if account_id is not None else None
