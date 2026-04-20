"""
ARQUIVO: actions de gerenciamento de perfis operacionais.

POR QUE ELE EXISTE:
- tira de `access/views.py` as mutacoes de create, update e toggle de perfis.
"""

from django.contrib.auth import get_user_model
from django.db import transaction

from .forms import AccessProfileCreateForm, AccessProfileUpdateForm


def split_access_full_name(full_name):
    chunks = full_name.split()
    if not chunks:
        return '', ''
    if len(chunks) == 1:
        return chunks[0], ''
    return chunks[0], ' '.join(chunks[1:])


def handle_access_profile_update(*, post_data, ensure_role_group):
    profile_id = post_data.get('target_profile_id', '').strip()
    form = AccessProfileUpdateForm(post_data, prefix=f'profile-{profile_id}')
    if not form.is_valid():
        forms_by_user_id = {}
        if profile_id.isdigit():
            forms_by_user_id[int(profile_id)] = form
        return {
            'ok': False,
            'reason': 'invalid-form',
            'forms_by_user_id': forms_by_user_id,
        }

    user_model = get_user_model()
    target_user = user_model.objects.filter(pk=profile_id).first()
    if target_user is None:
        return {
            'ok': False,
            'reason': 'not-found',
        }

    role_slug = form.cleaned_data['role']
    first_name, last_name = split_access_full_name(form.cleaned_data['full_name'])
    with transaction.atomic():
        target_user.first_name = first_name
        target_user.last_name = last_name
        target_user.email = form.cleaned_data['email']
        target_user.save(update_fields=['first_name', 'last_name', 'email'])
        group = ensure_role_group(role_slug)
        target_user.groups.set([group])

    return {
        'ok': True,
        'user': target_user,
    }


def handle_access_profile_toggle(*, actor, post_data):
    profile_id = post_data.get('target_profile_id', '').strip()
    user_model = get_user_model()
    target_user = user_model.objects.filter(pk=profile_id).first()
    if target_user is None:
        return {
            'ok': False,
            'reason': 'not-found',
        }
    if target_user.pk == actor.pk and target_user.is_active:
        return {
            'ok': False,
            'reason': 'self-disable-blocked',
        }

    target_user.is_active = not target_user.is_active
    target_user.save(update_fields=['is_active'])
    return {
        'ok': True,
        'user': target_user,
    }


def handle_access_profile_create(*, post_data, ensure_role_group):
    form = AccessProfileCreateForm(post_data)
    if not form.is_valid():
        return {
            'ok': False,
            'reason': 'invalid-form',
            'form': form,
        }

    user_model = get_user_model()
    username = form.cleaned_data['username']
    if user_model.objects.filter(username=username).exists():
        form.add_error('username', 'Ja existe um usuario com esse identificador.')
        return {
            'ok': False,
            'reason': 'duplicate-username',
            'form': form,
        }

    role_slug = form.cleaned_data['role']
    first_name, last_name = split_access_full_name(form.cleaned_data['full_name'])
    with transaction.atomic():
        user = user_model.objects.create_user(
            username=username,
            email=form.cleaned_data['email'],
            password=form.cleaned_data['password'],
            first_name=first_name,
            last_name=last_name,
        )
        group = ensure_role_group(role_slug)
        user.groups.set([group])

    return {
        'ok': True,
        'user': user,
        'group': group,
    }
