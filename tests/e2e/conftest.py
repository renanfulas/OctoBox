"""
ARQUIVO: fixtures para testes E2E do OctoBox.

POR QUE EXISTE:
- Configura o ambiente de browser (base_url) e os dados de banco necessários
  para que os testes E2E encontrem um servidor rodando com dados reais.

PONTOS CRÍTICOS:
- e2e_owner_credentials é session-scoped: o usuario é criado uma vez por sessão
  pytest com django_db_blocker.unblock() — dados commitados, visíveis ao thread
  do live_server.
- Depende de test_tenant (raiz/conftest.py) que cria Box(slug='test') e migra
  o schema box_test. Sem isso, TenantBySessionMiddleware retorna 403 ao tentar
  resolver o tenant do usuario.
- pytest-playwright fornece a fixture `page` automaticamente quando o pacote
  está instalado. Esta conftest só adiciona o que é específico do OctoBox.
"""

import pytest


@pytest.fixture(scope='session')
def base_url(live_server):
    """URL base do servidor Django de testes para o pytest-playwright."""
    return live_server.url


@pytest.fixture(scope='session')
def e2e_owner_credentials(test_tenant, django_db_blocker):
    """
    Cria (ou reutiliza) um usuário Owner com Membership no Box de teste.

    Retorna um dict com username e password para uso nos testes.
    Não retorna o objeto User para evitar problemas de acesso cross-thread
    a instâncias de modelo Django.

    Por que session scope?
    - Criar schema + bootstrap_roles + usuario a cada teste E2E levaria ~5s.
    - Como o live_server também é session-scoped, o banco persiste durante
      toda a sessão pytest E2E.
    """
    username = '__e2e_owner__'
    password = 'E2E-senha-forte-456'

    with django_db_blocker.unblock():
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Group
        from django.core.management import call_command
        from django_tenants.utils import schema_context

        from access.roles import ROLE_OWNER
        from control.models import Membership

        User = get_user_model()

        # bootstrap_roles cria os Groups necessários (idempotente).
        call_command('bootstrap_roles', verbosity=0)

        user, _ = User.objects.get_or_create(
            username=username,
            defaults={'email': 'e2e-owner@example.test'},
        )
        user.set_password(password)
        user.save()

        try:
            owner_group = Group.objects.get(name=ROLE_OWNER)
            user.groups.add(owner_group)
        except Group.DoesNotExist:
            pass

        # Membership liga o usuario ao Box de teste — sem isso,
        # TenantBySessionMiddleware retorna 403 ao tentar resolver o tenant.
        Membership.objects.get_or_create(
            user=user,
            box=test_tenant,
            defaults={
                'role': Membership.Role.OWNER,
                'is_primary_box': True,
            },
        )

    return {'username': username, 'password': password}
