"""
ARQUIVO: bootstrap pytest cross-project para django-tenants.

POR QUE EXISTE:
- Tests escritos antes do Sprint 2 usam django.test.TestCase com
  Student.objects.create(...) sem qualquer tenant_context. Com schema-per-tenant
  (boxcore em TENANT_APPS), boxcore_student so existe em schemas box_xxx,
  nunca em public. Sem este conftest, todos os tests que tocam modelos
  per-tenant falham com 'relation "boxcore_student" does not exist'.

O QUE ESTE ARQUIVO FAZ:
1. Cria um Box de teste (slug='test', schema_name='box_test') uma vez por
   sessao pytest (fixture de escopo session).
2. Roda migrate_schemas no schema do tenant para criar as tabelas
   TENANT_APPS dentro de box_test.
3. Auto-aplica schema_context('box_test') a cada test (autouse), de modo
   que ORM queries durante o test resolvem para o schema do tenant ao
   inves de public.

REQUISITOS DE EXECUCAO:
- pytest precisa rodar com --create-db --migrations (override do
  --reuse-db --nomigrations default em pytest.ini), senao migrate_schemas
  nao consegue criar as tabelas TENANT_APPS no schema do tenant.
- DATABASE_URL apontando para PostgreSQL real (django-tenants nao funciona
  em SQLite).

LIMITES CONHECIDOS:
- O autouse schema_context envolve TODO test, mesmo os que so usam modelos
  SHARED_APPS. Inofensivo (search_path inclui public como fallback) mas
  adiciona overhead minimo. Aceitavel no pilot.
- Tests que NAO usam o fixture 'db' (ex.: testes puros de funcoes utility)
  ainda recebem o wrap. Tambem inofensivo.

PONTOS CRITICOS:
- Quando o test DB usa SQLite (sem PostgreSQL), config/settings/test.py ja
  remove django_tenants do INSTALLED_APPS e TenantSyncRouter. Neste cenario,
  o conftest detecta a ausencia de django_tenants e vira no-op.
"""

from __future__ import annotations

import pytest


def _django_tenants_active() -> bool:
    """True quando django_tenants esta em INSTALLED_APPS (modo PostgreSQL)."""
    from django.conf import settings
    return 'django_tenants' in settings.INSTALLED_APPS


@pytest.fixture(scope='session')
def test_tenant(django_db_setup, django_db_blocker):
    """Cria (ou reusa) o Box de teste e garante que o schema esta migrado.

    Idempotente: usa get_or_create por slug. Se o schema box_test ja existe
    (re-execucao de pytest com --reuse-db), pula CREATE SCHEMA mas re-aplica
    migrate_schemas (idempotente — Django so aplica migrations pendentes).
    """
    if not _django_tenants_active():
        # SQLite fallback (test.py removeu django_tenants). Retorna None para
        # indicar que tests devem rodar sem tenant_context.
        return None

    from django.contrib.auth import get_user_model
    from django.core.management import call_command
    from django.db import connection
    from control.models import Box

    User = get_user_model()
    slug = 'test'
    schema_name = f'box_{slug}'

    with django_db_blocker.unblock():
        owner, _ = User.objects.get_or_create(
            username='__pytest_test_tenant_owner__',
            defaults={'email': '__pytest__@example.test'},
        )
        box, created = Box.objects.get_or_create(
            slug=slug,
            defaults={
                'schema_name': schema_name,
                'display_name': 'Pytest Test Tenant',
                'status': Box.Status.ACTIVE,
                'owner_user': owner,
            },
        )

        # CREATE SCHEMA (idempotente — IF NOT EXISTS)
        with connection.cursor() as cur:
            cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"')

        # Aplica TENANT_APPS migrations no schema do tenant.
        # migrate_schemas com --schema=xxx aplica apenas as TENANT_APPS no
        # schema indicado (sem reaplicar SHARED_APPS no public).
        call_command(
            'migrate_schemas',
            schema=schema_name,
            verbosity=0,
            interactive=False,
        )

    return box


@pytest.fixture(autouse=True)
def _tenant_schema_context(request, test_tenant):
    """Envolve cada test em schema_context do test_tenant.

    Sem este wrap, queries ORM resolvem para public schema (default),
    onde tabelas TENANT_APPS nao existem e queries falham com
    'relation does not exist'.

    Quando django_tenants nao esta ativo (SQLite fallback), test_tenant
    e None — pula o context manager e roda o test diretamente.
    """
    if test_tenant is None:
        yield
        return

    from django_tenants.utils import schema_context
    with schema_context(test_tenant.schema_name):
        yield
