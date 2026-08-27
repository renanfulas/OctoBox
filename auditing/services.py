"""
ARQUIVO: servicos de auditoria.

POR QUE ELE EXISTE:
- Evita espalhar criacao manual de eventos sensiveis pelo projeto.

O QUE ESTE ARQUIVO FAZ:
1. Traduz um alvo opcional em dados persistiveis.
2. Cria eventos padronizados de auditoria.
3. Mantem a escrita da trilha de auditoria em um unico ponto.
4. Garante que a escrita acontece num schema de tenant valido — caso a
   chamada venha de um path PUBLIC_SCHEMA (login, webhook, signup), faz
   resolucao defensiva do tenant antes da escrita.

PONTOS CRITICOS:
- O formato do evento precisa permanecer estavel para futuras consultas e relatorios.
- AuditEvent vive em TENANT_APPS (boxcore_auditevent); INSERT em schema=public
  estoura ProgrammingError. Para fluxos pre-auth ou cross-tenant (login,
  logout, webhook integration) precisamos ativar um tenant valido antes
  da escrita ou aceitar best-effort. Esse contrato esta resolvido pelo
  _ensure_tenant_for_audit_write abaixo, espelhando o padrao Center Layer
  usado em student_identity/facade/tenant_resolver.py para o aluno — MAS
  NAO e o mesmo padrao (ver Onda 5 do plano de correcao): o facade do aluno
  tem 8 call sites que dependem, por contrato, do tenant continuar ativo
  depois da chamada; aqui e o oposto, o tenant SEMPRE precisa voltar ao que
  era antes. Nao copiar o padrao de um pro outro.
- Onda 5a (2026-08-26): _write_audit_event e log_audit_event restauram
  connection.tenant ao valor de ANTES da chamada, apos escrever o evento.
  Antes disso, _ensure_tenant_for_audit_write ativava um tenant e nunca
  desfazia — inofensivo com um box so (nao ha pra onde vazar), mas deixa
  de ser inofensivo no instante em que existir um segundo Box ACTIVE. O
  restore NAO fica dentro de _ensure_tenant_for_audit_write (quebraria os
  7 testes de branch que ja existem para ela, que asseram chamadas de
  set_tenant) — fica nos dois CALLERS, capturando o tenant anterior antes
  de chamar e devolvendo depois, nunca hardcoded para public (haveria
  callers, ex. webhook do Resend, que ativam o tenant ANTES de chamar a
  auditoria, dentro do proprio transaction.atomic deles — resetar para
  public no meio dessa transacao quebraria a escrita que ainda vai commitar).
- Esta funcao (log_audit_event, antes internamente chamada via
  "async_log_audit_event") NUNCA foi assincrona: o import do Celery estava
  comentado e nada chamava .delay(). Renomeada para _write_audit_event —
  nome que nao promete o que o codigo nao faz.
"""

from django.apps import apps


def _ensure_tenant_for_audit_write(actor):
    """Garante schema valido para escrita de boxcore.AuditEvent.

    Ordem de strategies (primeira que resolver vence):
    1. Se connection.schema_name ja e tenant (!= 'public'), no-op.
    2. Se actor tem Membership com is_primary_box=True, ativa esse Box.
    3. Se ha exatamente 1 Box ATIVO no sistema (pilot/single-box), ativa.

    Retorna o Box ativado (ou None se nada resolveu). Em caso None, o
    caller deve envolver a escrita em try/except — INSERT em public falha.
    """
    try:
        from django.db import connection
        schema = getattr(connection, 'schema_name', None)
        if schema and schema != 'public':
            return None  # ja em tenant; no-op

        from control.models import Box, Membership

        # Strategy 2: actor's primary box
        if actor is not None and getattr(actor, 'pk', None):
            try:
                membership = (
                    Membership.objects
                    .select_related('box')
                    .filter(user=actor, is_primary_box=True, box__status=Box.Status.ACTIVE)
                    .first()
                )
                if membership is not None:
                    connection.set_tenant(membership.box)
                    return membership.box
            except Exception:
                pass

        # Strategy 3: single active box (pilot fallback)
        try:
            boxes = list(Box.objects.filter(status=Box.Status.ACTIVE)[:2])
            if len(boxes) == 1:
                connection.set_tenant(boxes[0])
                return boxes[0]
        except Exception:
            pass
    except Exception:
        pass
    return None


def _write_audit_event(actor_id, action, target_model, target_id, target_label, description, metadata):
    """Escreve o AuditEvent. Sincrona (ver nota de nomenclatura no topo do arquivo).

    Restaura connection.tenant ao valor de antes da chamada — ver docstring
    do módulo. `previous` é capturado ANTES de _ensure_tenant_for_audit_write
    poder mudá-lo, e é o que volta no finally, nunca um valor fixo.

    O INSERT roda dentro de transaction.atomic() — ausente antes desta onda,
    apesar do ADR-008 prescrever o trio "facade + savepoint + try/except" e
    listar este arquivo como implementação. Sem savepoint, uma falha aqui
    (ex.: schema sem boxcore_auditevent) corrompe qualquer transação externa
    que já estivesse em andamento — o próximo `except Exception: pass` pega a
    exceção, mas a transação já morreu, e a PRÓXIMA query de QUALQUER tipo,
    inclusive fora deste módulo, levanta TransactionManagementError. Django
    trata atomic() aninhado como SAVEPOINT automaticamente — não precisa de
    lógica extra para detectar se já existe uma transação em andamento.
    """
    from django.contrib.auth.models import User
    from django.db import connection, transaction
    from auditing.models import AuditEvent
    from auditing.scrubber import PIIScrubber

    actor = User.objects.filter(pk=actor_id).first() if actor_id else None
    role_slug = ''
    if actor:
        from access.roles import get_user_role
        role = get_user_role(actor)
        role_slug = getattr(role, 'slug', '')

    previous_tenant = getattr(connection, 'tenant', None)
    _ensure_tenant_for_audit_write(actor)
    try:
        with transaction.atomic():
            AuditEvent.objects.create(
                actor=actor,
                actor_role=role_slug,
                action=action,
                target_model=target_model,
                target_id=target_id,
                target_label=target_label,
                description=description,
                metadata=PIIScrubber.sanitize(metadata or {}),
            )
    except Exception:
        # Audit best-effort: se schema sem boxcore_auditevent e
        # _ensure_tenant_for_audit_write nao conseguiu ativar tenant (ex.:
        # multi-tenant prod com actor sem primary_box), nao bloquear o
        # fluxo principal (login/logout/webhook). O savepoint acima garante
        # que so o INSERT falho e desfeito — a transacao externa sobrevive.
        pass
    finally:
        if getattr(connection, 'tenant', None) is not previous_tenant:
            if previous_tenant is not None:
                connection.set_tenant(previous_tenant)
            else:
                connection.set_schema_to_public()


def log_platform_audit_event(*, actor=None, kind, target_box=None, description='', metadata=None):
    """Escreve um PlatformAuditEvent (SHARED_APP, vive em public).

    Onda 5b (2026-08-26, docs/plans/ondas-correcao-tenancy-billing-2026-08-25.md,
    ver ADR-006/ADR-008): usar para eventos que são de PLATAFORMA por
    natureza, não de um box especifico — login/logout de staff é o
    primeiro caso (um usuário multi-box não "pertence" a um box no
    momento do login; a sessão só escolhe um box DEPOIS).

    Diferença crucial em relação a log_audit_event/_write_audit_event:
    PlatformAuditEvent é SHARED_APP — a escrita funciona de QUALQUER
    schema, inclusive public, sem precisar de _ensure_tenant_for_audit_write
    nem do fallback SINGLE_ACTIVE_BOX. Não existe mais "best-effort que
    falha quando não há box pra ativar" para os eventos que passarem a
    usar esta função — a escrita sempre funciona, independente de quantos
    boxes existem ou se o actor tem Membership.

    target_box: deliberadamente None por padrão. Não adivinha o box do
    actor (ex.: via primary Membership) — um login não necessariamente
    corresponde ao box que o usuário vai escolher trabalhar depois, e
    atribuir a um box errado é pior que não atribuir. Callers que SABEM
    o box relevante (billing, provisioning) devem passar explicitamente.

    description/metadata não têm campo dedicado em PlatformAuditEvent
    (só kind + payload) — ambos vão dentro de payload, sanitizados pelo
    PIIScrubber (nenhum dos 3 call sites que já criavam PlatformAuditEvent
    direto — control/services.py, integrations/stripe/router.py — aplicava
    isso; ficam como estão, fora do escopo desta onda, mas o caminho novo
    não repete a lacuna).
    """
    from auditing.scrubber import PIIScrubber
    from control.models import PlatformAuditEvent

    role_slug = ''
    if actor is not None:
        from access.roles import get_user_role
        role = get_user_role(actor)
        role_slug = getattr(role, 'slug', '')

    payload = dict(metadata or {})
    if description:
        payload['description'] = description
    if role_slug:
        payload['actor_role'] = role_slug

    try:
        return PlatformAuditEvent.objects.create(
            actor_user=actor,
            target_box=target_box,
            kind=kind,
            payload=PIIScrubber.sanitize(payload),
        )
    except Exception:
        # Mesma filosofia best-effort do ADR-008: auditoria nunca derruba
        # o fluxo principal (login/logout). Diferente do caminho antigo,
        # a falha aqui só pode vir de algo genuinamente excepcional (banco
        # fora do ar) — não de "não achei schema pra ativar".
        return None


def log_audit_event(*, actor=None, action, target=None, description='', metadata=None):
    from config.settings.base import is_local_runtime_mode

    target_model = ''
    target_id = ''
    target_label = ''
    if target is not None and hasattr(target, '_meta'):
        target_model = target._meta.model_name
        target_id = str(target.pk)
        target_label = str(target)

    actor_id = getattr(actor, 'id', None)

    if is_local_runtime_mode():
        # Caminho local/dev: mesma escrita, mas sem passar pelo _write_audit_event
        # (evita reconsultar o User por pk quando já temos o objeto `actor`).
        # Mesmo par savepoint+restore de _write_audit_event — ver docstring dela.
        from django.db import connection, transaction
        from auditing.models import AuditEvent
        from auditing.scrubber import PIIScrubber
        from access.roles import get_user_role
        role = get_user_role(actor) if actor is not None else None
        previous_tenant = getattr(connection, 'tenant', None)
        _ensure_tenant_for_audit_write(actor)
        try:
            with transaction.atomic():
                return AuditEvent.objects.create(
                    actor=actor,
                    actor_role=getattr(role, 'slug', ''),
                    action=action,
                    target_model=target_model,
                    target_id=target_id,
                    target_label=target_label,
                    description=description,
                    metadata=PIIScrubber.sanitize(metadata or {}),
                )
        except Exception:
            # Audit best-effort: ver justificativa em _write_audit_event.
            return None
        finally:
            if getattr(connection, 'tenant', None) is not previous_tenant:
                if previous_tenant is not None:
                    connection.set_tenant(previous_tenant)
                else:
                    connection.set_schema_to_public()
    else:
        _write_audit_event(
            actor_id=actor_id,
            action=action,
            target_model=target_model,
            target_id=target_id,
            target_label=target_label,
            description=description,
            metadata=metadata
        )
