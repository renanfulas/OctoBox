"""
ARQUIVO: resolucao de tenant para fluxos pre-auth do aluno (Center Layer).

POR QUE EXISTE:
- consolida em UM lugar as estrategias para descobrir qual Box deve ser
  ativado quando o request do aluno chega em rotas publicas (/aluno/auth/*)
  sem cookie de sessao ainda.
- antes, essa logica estava espalhada em:
    student_identity/oauth_actions.py (_activate_identity_tenant)
    student_identity/oauth_journeys.py (_activate_box_tenant)
    student_identity/views.py (chamada ad-hoc)
- cada lugar implementava sua estrategia parcial e algumas combinacoes de
  inputs (ex.: OAuth callback sem invite_token + identity nao existente
  ainda) caiam em buracos de cobertura.

CENTER LAYER (docs/architecture/center-layer.md):
- "novos fluxos externos devem preferir entrar por uma facade do CENTER"
- este modulo formaliza a porta de entrada para tenant resolution
  pre-auth. Strategies sao explicitas e ordenadas; novas strategies
  entram aqui, nao espalhadas no codigo.

ANTI-PATTERN PROIBIDO:
- adicionar mais uma chamada `connection.set_tenant(...)` ad-hoc em outro
  modulo. Se precisar de uma nova estrategia, ELA ENTRA AQUI.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from django.db import connection


class StudentAuthTenantStrategy(str, Enum):
    """Categorias de origem da resolucao do tenant pre-auth.

    Usado para diagnostico/audit. Ordem reflete prioridade.
    """
    INVITATION = 'invitation'             # token de convite individual aponta para box
    INVITE_LINK = 'invite_link'           # token de link em massa aponta para box
    EXISTING_IDENTITY_BY_SUBJECT = 'existing_identity_by_subject'  # OAuth retorna, ja existe identity
    EXISTING_IDENTITY_BY_EMAIL = 'existing_identity_by_email'      # email corresponde 1:1 a identity
    SINGLE_ACTIVE_BOX = 'single_active_box'  # pilot/single-box fallback: 1 box ATIVO no sistema
    NONE = 'none'                         # nenhuma estrategia resolveu


@dataclass(frozen=True)
class TenantResolution:
    """Result estavel da tentativa de resolver tenant.

    box: Box ATIVADO na connection (set_tenant ja chamado), ou None se
         nenhuma estrategia resolveu.
    strategy: estrategia que conseguiu resolver (ou NONE).
    box_root_slug: schema_name do box, replicado aqui para conveniencia
                   de logs/audit sem forcar acesso a connection.

    Apos receber esta resolution, callers NAO precisam chamar
    `connection.set_tenant()` — ja foi feito (ou nao foi possivel).
    """
    box: Optional[object]  # control.Box ou None
    strategy: StudentAuthTenantStrategy
    box_root_slug: str = ''


def _activate_box(box) -> None:
    """Helper interno: ativa o Box na connection corrente."""
    connection.set_tenant(box)


def _find_box_by_id_or_slug(box_id=None, box_root_slug: str = ''):
    """Recupera um Box por pk (caminho preferido) ou por schema_name (fallback).

    Centraliza o pattern duplicado em oauth_journeys._activate_box_tenant
    e oauth_actions._activate_identity_tenant.
    """
    from control.models import Box

    if not box_id and not box_root_slug:
        return None
    try:
        if box_id:
            return Box.objects.get(pk=box_id, status=Box.Status.ACTIVE)
        return (
            Box.objects.filter(schema_name=box_root_slug, status=Box.Status.ACTIVE).first()
            or Box.objects.filter(slug=box_root_slug, status=Box.Status.ACTIVE).first()
        )
    except Exception:
        return None


def _resolve_from_invite_token(invite_token: str) -> Optional[TenantResolution]:
    """Strategy 1+2: invite_token aponta para Box (via invitation OU link).

    Retorna TenantResolution se conseguir, ou None se invite_token vazio/invalido.
    """
    if not invite_token or not invite_token.strip():
        return None

    from student_identity.infrastructure.repositories import DjangoStudentIdentityRepository
    repo = DjangoStudentIdentityRepository()

    invitation = repo.find_invitation_by_token(invite_token.strip())
    if invitation is not None:
        box = _find_box_by_id_or_slug(
            box_id=getattr(invitation, 'box_id', None),
            box_root_slug=getattr(invitation, 'box_root_slug', '') or '',
        )
        if box is not None:
            _activate_box(box)
            return TenantResolution(
                box=box,
                strategy=StudentAuthTenantStrategy.INVITATION,
                box_root_slug=box.schema_name,
            )

    link = repo.find_box_invite_link_by_token(invite_token.strip())
    if link is not None:
        box = _find_box_by_id_or_slug(
            box_id=getattr(link, 'box_id', None),
            box_root_slug=getattr(link, 'box_root_slug', '') or '',
        )
        if box is not None:
            _activate_box(box)
            return TenantResolution(
                box=box,
                strategy=StudentAuthTenantStrategy.INVITE_LINK,
                box_root_slug=box.schema_name,
            )

    return None


def _resolve_from_existing_identity_by_subject(provider_subject: str) -> Optional[TenantResolution]:
    """Strategy 3: usuario ja autenticou antes — identity existe por provider_subject.

    Este caminho cobre o OAuth callback de usuario PRE-EXISTENTE sem
    invite_token, que era exatamente o gap do Bucket B do plano de
    qualidade de testes.
    """
    if not provider_subject or not provider_subject.strip():
        return None

    from student_identity.models import StudentIdentity
    identity = (
        StudentIdentity.objects
        .filter(provider_subject=provider_subject.strip().lower())
        .order_by('-last_authenticated_at', '-id')
        .first()
    )
    if identity is None:
        return None

    box = _find_box_by_id_or_slug(
        box_id=getattr(identity, 'box_id', None),
        box_root_slug=getattr(identity, 'box_root_slug', '') or '',
    )
    if box is None:
        return None

    _activate_box(box)
    return TenantResolution(
        box=box,
        strategy=StudentAuthTenantStrategy.EXISTING_IDENTITY_BY_SUBJECT,
        box_root_slug=box.schema_name,
    )


def _resolve_from_existing_identity_by_email(email: str) -> Optional[TenantResolution]:
    """Strategy 4: usuario tem identity em um (unico) box por email.

    Usado quando provider_subject mudou (ex.: app desinstalou e reinstalou
    o app OAuth provider gerando subject novo) mas email permanece.

    Retorna None se ha 0 ou >1 identities com aquele email (ambiguo).
    """
    if not email or not email.strip():
        return None

    from student_identity.models import StudentIdentity, StudentIdentityStatus
    candidates = list(
        StudentIdentity.objects
        .filter(email__iexact=email.strip(), status=StudentIdentityStatus.ACTIVE)
        .values('box_id', 'box_root_slug')
    )
    if len(candidates) != 1:
        return None

    box = _find_box_by_id_or_slug(
        box_id=candidates[0]['box_id'],
        box_root_slug=candidates[0]['box_root_slug'] or '',
    )
    if box is None:
        return None

    _activate_box(box)
    return TenantResolution(
        box=box,
        strategy=StudentAuthTenantStrategy.EXISTING_IDENTITY_BY_EMAIL,
        box_root_slug=box.schema_name,
    )


def _resolve_from_single_active_box() -> Optional[TenantResolution]:
    """Strategy 5 (fallback): pilot/single-box.

    Se HOUVER EXATAMENTE 1 Box ATIVO no sistema, usa ele. Cobre o caso:
        - aluno sem invite_token (URL direta /aluno/auth/login/)
        - aluno sem identity previa (primeiro login OAuth)
        - sem identity matching por email
    Em pilot single-box, esse e o cenario normal de "primeiro acesso".

    LIMITE EXPLICITO: em prod multi-tenant (N > 1 boxes), retorna None.
    O caller deve forcar invite_token, subdomain-based routing, ou
    outra estrategia explicita.
    """
    from control.models import Box
    try:
        boxes = list(Box.objects.filter(status=Box.Status.ACTIVE)[:2])
    except Exception:
        return None
    if len(boxes) != 1:
        return None
    box = boxes[0]
    _activate_box(box)
    return TenantResolution(
        box=box,
        strategy=StudentAuthTenantStrategy.SINGLE_ACTIVE_BOX,
        box_root_slug=box.schema_name,
    )


def resolve_tenant_for_student_oauth_callback(
    *,
    invite_token: str = '',
    provider_subject: str = '',
    email: str = '',
) -> TenantResolution:
    """Resolve tenant para um OAuth callback do aluno.

    Ordem de strategies (primeira que resolver vence):
    1. invite_token via invitation
    2. invite_token via link em massa
    3. provider_subject -> existing identity
    4. email -> existing identity (so se houver exatamente 1)
    5. single active box (pilot fallback, nao vale em multi-tenant)

    Apos retorno, a connection ja esta ATIVADA no schema do box
    (caller pode rodar queries TENANT_APPS imediatamente).

    Retorna TenantResolution com box=None e strategy=NONE se nada resolveu.
    """
    resolution = _resolve_from_invite_token(invite_token)
    if resolution is not None:
        return resolution

    resolution = _resolve_from_existing_identity_by_subject(provider_subject)
    if resolution is not None:
        return resolution

    resolution = _resolve_from_existing_identity_by_email(email)
    if resolution is not None:
        return resolution

    resolution = _resolve_from_single_active_box()
    if resolution is not None:
        return resolution

    return TenantResolution(box=None, strategy=StudentAuthTenantStrategy.NONE)


def resolve_tenant_for_student_invite_landing(*, invite_token: str) -> TenantResolution:
    """Resolve tenant para o landing de convite (/aluno/auth/invite/<token>).

    Forma simplificada do callback: so faz sentido com invite_token.
    """
    resolution = _resolve_from_invite_token(invite_token)
    if resolution is not None:
        return resolution
    return TenantResolution(box=None, strategy=StudentAuthTenantStrategy.NONE)
