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


def load_coach_workout_editor_session(*, session_id):
    return get_object_or_404(
        ClassSession.objects.select_related('coach', 'workout').prefetch_related(
            'attendances__student',
            'workout__blocks__movements',
        ),
        pk=session_id,
    )


__all__ = ['load_coach_workout_editor_session']
