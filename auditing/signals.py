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
"""

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from auditing.services import log_audit_event


@receiver(user_logged_in, dispatch_uid='auditing_user_logged_in')
def audit_user_logged_in(sender, request, user, **kwargs):
    log_audit_event(
        actor=user,
        action='user_login',
        description='Usuario autenticado iniciou sessao no sistema.',
        metadata={
            'path': getattr(request, 'path', ''),
            'method': getattr(request, 'method', ''),
        },
    )


@receiver(user_logged_out, dispatch_uid='auditing_user_logged_out')
def audit_user_logged_out(sender, request, user, **kwargs):
    log_audit_event(
        actor=user,
        action='user_logout',
        description='Usuario autenticado encerrou sessao no sistema.',
        metadata={
            'path': getattr(request, 'path', ''),
            'method': getattr(request, 'method', ''),
        },
    )
