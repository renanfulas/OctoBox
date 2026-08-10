"""
ARQUIVO: actions de gerenciamento de perfis operacionais.

POR QUE ELE EXISTE:
- tira de `access/views.py` as mutacoes de create, update, toggle e reset de senha.

PONTOS CRITICOS:
- `handle_access_profile_password_reset` e a saida de emergencia do fluxo por
  e-mail (access/password_reset.py): cobre funcionario sem e-mail cadastrado,
  sem acesso a caixa de entrada, ou com pressa no balcao. A senha gerada e
  devolvida em texto UMA vez para o gestor ler em voz alta — nunca e persistida
  em claro nem logada, inclusive no AuditEvent.
"""

import secrets

from django.contrib.auth import get_user_model
from django.db import transaction

from auditing import log_audit_event

from .forms import AccessProfileCreateForm, AccessProfileUpdateForm


# Alfabeto sem caracteres ambiguos (0/O, 1/l/I) — a senha e lida em voz alta ou
# copiada a mao no balcao do box, entao confundir caractere custa suporte.
_PROVISIONAL_PASSWORD_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'  # gitleaks:allow -- alfabeto de geracao, nao segredo
_PROVISIONAL_PASSWORD_LENGTH = 14


def build_provisional_password() -> str:
    """Gera senha provisoria com entropia de CSPRNG (~80 bits no tamanho atual)."""
    return ''.join(
        secrets.choice(_PROVISIONAL_PASSWORD_ALPHABET)
        for _ in range(_PROVISIONAL_PASSWORD_LENGTH)
    )


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


def handle_access_profile_password_reset(*, actor, post_data):
    """Redefine a senha de um funcionario para uma provisoria, gerada na hora.

    Existe para o caso que o fluxo por e-mail nao cobre: conta sem e-mail
    cadastrado, ou funcionario que precisa entrar agora e nao tem acesso a
    caixa de entrada. O gestor passa a senha presencialmente.

    O gestor NAO pode resetar a propria senha por aqui — para isso existe o
    fluxo por e-mail. Sem essa trava, uma sessao sequestrada de owner trocaria
    a senha do dono sem passar por nenhum segundo fator.
    """
    profile_id = post_data.get('target_profile_id', '').strip()
    user_model = get_user_model()
    target_user = user_model.objects.filter(pk=profile_id).first()
    if target_user is None:
        return {
            'ok': False,
            'reason': 'not-found',
        }
    if target_user.pk == actor.pk:
        return {
            'ok': False,
            'reason': 'self-reset-blocked',
        }

    provisional_password = build_provisional_password()
    with transaction.atomic():
        target_user.set_password(provisional_password)
        target_user.save(update_fields=['password'])

    # Trocar o hash da senha invalida qualquer link de recuperacao pendente
    # dessa conta (o default_token_generator assina o hash atual). Efeito
    # desejado: reset presencial cancela o reset por e-mail em voo.

    # Trilha obrigatoria: alguem trocou a credencial de outra pessoa. A senha
    # NUNCA entra no metadata — so o fato, o autor e o alvo.
    log_audit_event(
        actor=actor,
        action='access_profile_password_reset',
        target=target_user,
        description=f'Senha provisoria emitida para {target_user.username} pela tela de acessos.',
        metadata={'target_username': target_user.username, 'channel': 'manager_provisional'},
    )

    return {
        'ok': True,
        'user': target_user,
        'provisional_password': provisional_password,
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
        form.add_error('username', 'Já existe um usuário com esse identificador.')
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
