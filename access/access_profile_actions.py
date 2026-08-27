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
- Onda 1-pre (2026-08-26): create/update passaram a manter control.Membership
  em sincronia com o Group escolhido no form. access.roles.get_user_role lê
  Membership.role ANTES de Group — sem este sync, criar um perfil o deixaria
  sem Membership (sumindo da listagem escopada por box da Onda 1b) e editar
  o papel de alguém que já tem Membership viraria no-op silencioso.
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


def _guard_target_is_manageable(*, target_user, box):
    """Recusa alvo fora do escopo do ator: superusuário sempre, e qualquer
    usuário com Membership em OUTRO box (nega cross-box).

    ONDA 1a — FASE 1 (antes do backfill de Onda 1-pré estar confirmado em
    produção, via `manage.py backfill_staff_membership`). NÃO recusa ainda
    alvo sem Membership nenhuma: staff legado não migrado continuaria
    gerenciável, para não travar operação real antes do backfill rodar.
    Apertar para "recusa alvo sem Membership no box do ator" é a fase 2,
    só depois do backfill confirmado — ver docs/plans/ondas-correcao-
    tenancy-billing-2026-08-25.md, Onda 1.

    Retorna uma reason string se deve recusar, ou None se o alvo é gerenciável.
    """
    if target_user.is_superuser:
        return 'superuser-target-denied'

    if box is not None:
        from control.models import Membership

        has_membership_elsewhere = (
            Membership.objects.filter(user=target_user).exclude(box=box).exists()
        )
        if has_membership_elsewhere:
            return 'cross-box-denied'

    return None


def _sync_membership_role(*, user, box, role_slug):
    """Cria ou atualiza o Membership do usuário neste box com o papel escolhido.

    is_primary_box só é setado True na CRIAÇÃO — update não mexe nisso, para
    não atropelar o box primário de um usuário multi-box (ex.: superdev)
    sendo editado a partir de outro box.

    Retorna None (no-op) se role_slug não tem Membership.Role equivalente —
    não deveria acontecer via form (OPERATIONAL_ROLE_CHOICES já filtra fora
    o único caso sem equivalente, honeypot), mas falha aberta em vez de
    levantar: perfil criado/editado sem Membership não é pior que o estado
    anterior a esta onda, só não corrige o gap.
    """
    from control.models import Membership
    from access.roles import SLUG_TO_MEMBERSHIP_ROLE

    membership_role = SLUG_TO_MEMBERSHIP_ROLE.get(role_slug)
    if membership_role is None or box is None:
        return None

    membership, created = Membership.objects.get_or_create(
        user=user,
        box=box,
        defaults={'role': membership_role, 'is_primary_box': True},
    )
    if not created and membership.role != membership_role:
        membership.role = membership_role
        membership.save(update_fields=['role'])
    return membership


def handle_access_profile_update(*, post_data, ensure_role_group, box=None):
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

    denial_reason = _guard_target_is_manageable(target_user=target_user, box=box)
    if denial_reason is not None:
        return {
            'ok': False,
            'reason': denial_reason,
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
        _sync_membership_role(user=target_user, box=box, role_slug=role_slug)

    return {
        'ok': True,
        'user': target_user,
    }


def handle_access_profile_toggle(*, actor, post_data, box=None):
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

    denial_reason = _guard_target_is_manageable(target_user=target_user, box=box)
    if denial_reason is not None:
        return {
            'ok': False,
            'reason': denial_reason,
        }

    target_user.is_active = not target_user.is_active
    target_user.save(update_fields=['is_active'])
    return {
        'ok': True,
        'user': target_user,
    }


def handle_access_profile_password_reset(*, actor, post_data, box=None):
    """Redefine a senha de um funcionario para uma provisoria, gerada na hora.

    Existe para o caso que o fluxo por e-mail nao cobre: conta sem e-mail
    cadastrado, ou funcionario que precisa entrar agora e nao tem acesso a
    caixa de entrada. O gestor passa a senha presencialmente.

    O gestor NAO pode resetar a propria senha por aqui — para isso existe o
    fluxo por e-mail. Sem essa trava, uma sessao sequestrada de owner trocaria
    a senha do dono sem passar por nenhum segundo fator.

    ONDA 1a: alvo superusuário ou com Membership em outro box é recusado por
    _guard_target_is_manageable — é o caminho que permitia Owner de um box
    resetar a senha do superdev (ou de staff de outro box) e recebê-la em
    texto na tela. Ver docs/plans/ondas-correcao-tenancy-billing-2026-08-25.md,
    Onda 1.
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

    denial_reason = _guard_target_is_manageable(target_user=target_user, box=box)
    if denial_reason is not None:
        return {
            'ok': False,
            'reason': denial_reason,
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


def handle_access_profile_create(*, post_data, ensure_role_group, box=None):
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
        _sync_membership_role(user=user, box=box, role_slug=role_slug)

    return {
        'ok': True,
        'user': user,
        'group': group,
    }
