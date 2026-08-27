"""
ARQUIVO: sinais de auditoria de autenticacao.

POR QUE ELE EXISTE:
- Registra entrada e saida do sistema sem depender de logica espalhada nas views.

O QUE ESTE ARQUIVO FAZ:
1. Escuta login de usuario.
2. Escuta logout de usuario.
3. Cria eventos padronizados de auditoria para autenticacao.

PONTOS CRITICOS:
- Esses sinais precisam ser carregados no startup do app.
- O login logout deve continuar funcionando mesmo se a auditoria falhar futuramente.
- Onda 5b (2026-08-26, ver ADR-006/ADR-008 e docs/plans/ondas-correcao-
  tenancy-billing-2026-08-25.md): login/logout migraram de log_audit_event
  (AuditEvent, TENANT_APP — precisava de _ensure_tenant_for_audit_write
  achar ALGUM schema pra escrever) para log_platform_audit_event
  (PlatformAuditEvent, SHARED_APP — escreve de QUALQUER schema, sempre).
  Motivo: login/logout são eventos de plataforma, não de um box
  específico — um usuário multi-box não "pertence" a nenhum box no
  instante do login.
"""

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from auditing.services import log_platform_audit_event


@receiver(user_logged_in, dispatch_uid='auditing_user_logged_in')
def audit_user_logged_in(sender, request, user, **kwargs):
    log_platform_audit_event(
        actor=user,
        kind='auth.login',
        description='Usuario autenticado iniciou sessao no sistema.',
        metadata={
            'path': getattr(request, 'path', ''),
            'method': getattr(request, 'method', ''),
        },
    )


@receiver(user_logged_out, dispatch_uid='auditing_user_logged_out')
def audit_user_logged_out(sender, request, user, **kwargs):
    log_platform_audit_event(
        actor=user,
        kind='auth.logout',
        description='Usuario autenticado encerrou sessao no sistema.',
        metadata={
            'path': getattr(request, 'path', ''),
            'method': getattr(request, 'method', ''),
        },
    )
