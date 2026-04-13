"""
ARQUIVO: helpers leves de ownership da cascata por unidade.

POR QUE ELE EXISTE:
- centraliza a resolucao do owner mestre e do box do ator sem abrir a cascata completa agora.
- protege a fundacao barata contra logica duplicada e fallback espalhado.

PONTOS CRITICOS:
- este modulo precisa tolerar runtimes sem modelos Box/BoxUser carregados.
- quando o sistema ainda estiver em modo single-unit, o fallback deve ser explicito e previsivel.
"""

from __future__ import annotations

from django.apps import apps
from django.contrib.auth import get_user_model


def _load_box_user_model():
    for app_label, model_name in (('access', 'BoxUser'), ('boxcore', 'BoxUser')):
        try:
            return apps.get_model(app_label, model_name)
        except LookupError:
            continue
    for model in apps.get_models():
        if model.__name__ == 'BoxUser':
            return model
    return None


def _resolve_first_system_owner_user_id():
    user_model = get_user_model()
    master_owner = user_model.objects.filter(is_superuser=True).order_by('date_joined', 'id').first()
    if master_owner is not None:
        return master_owner.id
    fallback_user = user_model.objects.order_by('date_joined', 'id').first()
    return getattr(fallback_user, 'id', None)


def resolve_box_owner_user_id(box_id=None):
    box_user_model = _load_box_user_model()
    if box_user_model is not None and box_id not in (None, ''):
        relations = list(box_user_model.objects.filter(box_id=box_id).order_by('created_at', 'id')[:32])
        for relation in relations:
            role_slug = getattr(getattr(relation, 'role', None), 'slug', '')
            if role_slug == 'owner':
                return getattr(relation, 'user_id', None)
        if relations:
            return getattr(relations[0], 'user_id', None)
    return _resolve_first_system_owner_user_id()


def resolve_actor_box_id(actor=None, *, preferred_box_id=None):
    if preferred_box_id not in (None, ''):
        return preferred_box_id
    if actor is None:
        return None

    for attr_name in ('box_id', 'current_box_id', 'active_box_id'):
        attr_value = getattr(actor, attr_name, None)
        if attr_value not in (None, ''):
            return attr_value

    actor_id = getattr(actor, 'id', None)
    if actor_id is None:
        return None

    box_user_model = _load_box_user_model()
    if box_user_model is None:
        return None

    relation = box_user_model.objects.filter(user_id=actor_id).order_by('created_at', 'id').first()
    return getattr(relation, 'box_id', None) if relation is not None else None


__all__ = [
    'resolve_actor_box_id',
    'resolve_box_owner_user_id',
]
