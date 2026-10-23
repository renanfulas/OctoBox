"""
ARQUIVO: loader do editor de WOD do coach.

POR QUE ELE EXISTE:
- remove da view o carregamento detalhado da sessao do editor sem misturar loading com contexto ou mutacao.

O QUE ESTE ARQUIVO FAZ:
1. carrega a `ClassSession` do editor com relacionamentos necessarios.
2. concentra o preload do workout, blocos, movimentos e presencas.

PONTOS CRITICOS:
- manter os `select_related` e `prefetch_related` alinhados ao contrato do editor.
- qualquer regressao aqui afeta leitura, contexto e actions do WOD.
"""

from django.shortcuts import get_object_or_404

from operations.models import ClassSession
from access.roles import ROLE_COACH, get_user_role


def load_coach_workout_editor_session(*, session_id, actor=None):
    sessions = ClassSession.objects.select_related('coach', 'workout').prefetch_related(
        'attendances__student', 'workout__blocks__movements',
    )
    if actor is not None and actor.is_authenticated:
        role = get_user_role(actor)
        if role is not None and role.slug == ROLE_COACH:
            sessions = sessions.filter(coach=actor)
    return get_object_or_404(
        sessions,
        pk=session_id,
    )


__all__ = ['load_coach_workout_editor_session']
