#!/usr/bin/env bash
# =============================================================================
# provision_test_tenants.sh
#
# POR QUE EXISTE:
#   Os boundary tests B1–B12 (tests/test_tenant_boundary.py) precisam de dois
#   schemas separados para provar isolamento cross-tenant:
#     - box_test_a (slug=test-a)
#     - box_test_b (slug=test-b)
#
#   O conftest.py so provisiona box_test (slug=test). Este script cria os dois
#   tenants de isolamento com suas migrations aplicadas.
#
# COMO USAR:
#   # Local (requer docker-compose.test.yml rodando):
#   DATABASE_URL=postgres://postgres:postgres@localhost:5433/octobox_test \
#     bash scripts/provision_test_tenants.sh
#
#   # CI (rodado pelo job tenant-boundary em full-test-suite.yml):
#   bash scripts/provision_test_tenants.sh
#
# IDEMPOTENTE: pode rodar multiplas vezes sem erro.
#   - Se o tenant ja existe, apenas re-aplica migrate_schemas.
#   - CREATE SCHEMA usa IF NOT EXISTS.
#
# REQUISITOS:
#   - DJANGO_SETTINGS_MODULE setado (config.settings.test)
#   - DATABASE_URL apontando para PostgreSQL
#   - manage.py acessivel no CWD (raiz do projeto)
# =============================================================================

set -euo pipefail

MANAGE="python manage.py"
SETTINGS="${DJANGO_SETTINGS_MODULE:-config.settings.test}"

echo "==> Provisionando tenants de boundary test..."
echo "    Settings: ${SETTINGS}"
echo "    DATABASE_URL: ${DATABASE_URL:-<nao setado>}"

# Cria box_test_a e box_test_b via management command Python inline.
# Usar Python inline evita dependencia de um management command customizado.
$MANAGE shell --settings="$SETTINGS" << 'PYEOF'
from django.db import connection
from django.core.management import call_command
from django.contrib.auth import get_user_model

User = get_user_model()

try:
    from control.models import Box
except ImportError:
    print("ERRO: control.models.Box nao encontrado. Verifique INSTALLED_APPS.")
    raise

owner, _ = User.objects.get_or_create(
    username='__pytest_boundary_owner__',
    defaults={'email': '__boundary__@example.test'},
)

tenants = [
    {'slug': 'test-a', 'schema_name': 'box_test_a', 'display_name': 'Boundary Test A'},
    {'slug': 'test-b', 'schema_name': 'box_test_b', 'display_name': 'Boundary Test B'},
]

for t in tenants:
    box, created = Box.objects.get_or_create(
        slug=t['slug'],
        defaults={
            'schema_name': t['schema_name'],
            'display_name': t['display_name'],
            'status': Box.Status.ACTIVE,
            'owner_user': owner,
        },
    )
    action = 'Criado' if created else 'Ja existe'
    print(f"  [{action}] {t['slug']} -> schema {t['schema_name']}")

    # CREATE SCHEMA idempotente
    with connection.cursor() as cur:
        cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{t["schema_name"]}"')

    # Aplica TENANT_APPS migrations no schema
    call_command('migrate_schemas', schema=t['schema_name'], verbosity=1, interactive=False)

print("==> Provisionamento concluido.")
PYEOF

echo ""
echo "==> Tenants disponiveis para boundary tests:"
echo "    box_test_a  (slug=test-a)"
echo "    box_test_b  (slug=test-b)"
echo ""
echo "==> Para rodar os boundary tests:"
echo "    pytest tests/test_tenant_boundary.py -m requires_postgres -v"
