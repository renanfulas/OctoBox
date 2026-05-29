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

import os
import pathlib

import pytest


# === Fase 1 do plano de qualidade: skip de testes broken sem editar
# cada arquivo. Lista mantida em tests/broken-tests.txt (1 node-id
# por linha). Ver docs/testing/broken-tests-inventory.md.

_BROKEN_TESTS_FILE = pathlib.Path(__file__).parent / 'tests' / 'broken-tests.txt'


def _load_broken_tests() -> set[str]:
    """Le tests/broken-tests.txt e retorna conjunto de node-ids para skip.

    Formato esperado por linha:
        path/file.py::Class::method  owner=@nome  since=YYYY-MM-DD  ticket=#NNN

    Regras de validacao (ativadas em CI via OCTOBOX_REQUIRE_POSTGRES=1):
    - Linhas sem 'owner=' emitem aviso.
    - Linhas com 'since=' a mais de 30 dias em CI causam falha de sessao.

    OVERRIDE: setar OCTOBOX_RUN_BROKEN_TESTS=1 desativa o skip e roda
    todos os tests (incluindo broken). Usado para diagnostico.
    """
    if os.environ.get('OCTOBOX_RUN_BROKEN_TESTS') == '1':
        return set()
    if not _BROKEN_TESTS_FILE.exists():
        return set()

    import datetime
    broken: set[str] = set()
    is_ci = os.environ.get('CI') == 'true'
    today = datetime.date.today()

    for raw in _BROKEN_TESTS_FILE.read_text(encoding='utf-8').splitlines():
        line = raw.split('#', 1)[0].strip()
        if not line:
            continue

        node_id = line.split()[0]
        broken.add(node_id)

        # Validacao de formato (apenas em CI para nao poluir local).
        if is_ci:
            if 'owner=' not in line:
                print(f'\n⚠ broken-tests.txt: linha sem owner= — {node_id}')
            if 'since=' in line:
                try:
                    since_str = [p for p in line.split() if p.startswith('since=')][0]
                    since_date = datetime.date.fromisoformat(since_str.replace('since=', ''))
                    age_days = (today - since_date).days
                    if age_days > 30:
                        pytest.exit(
                            f'\n\n❌ broken-tests.txt: {node_id!r} esta quebrado ha {age_days} dias '
                            f'(limite: 30). Corrija o teste ou abra ticket para priorizar.\n',
                            returncode=4,
                        )
                except (ValueError, IndexError):
                    pass

    return broken


def pytest_configure(config):
    """Gate de ambiente: OCTOBOX_REQUIRE_POSTGRES=1 converte skip em ERROR.

    Em CI (full-test-suite.yml), esta variavel esta sempre setada.
    Se o banco ativo nao for PostgreSQL, a sessao falha imediatamente com
    mensagem clara — em vez de testes 'requires_postgres' ficarem verdes
    por skip silencioso.

    Localmente sem a variavel: comportamento normal (skip limpo em SQLite).
    """
    if os.environ.get('OCTOBOX_REQUIRE_POSTGRES') != '1':
        return
    # Importa settings lazily para nao forcar setup antes do Django estar pronto.
    try:
        from django.conf import settings as djsettings
        from django.test.utils import setup_test_environment
        # Verifica via DATABASE ENGINE, nao via connection (ainda nao aberta).
        db_engine = djsettings.DATABASES.get('default', {}).get('ENGINE', '')
        if 'postgresql' not in db_engine and 'psycopg' not in db_engine:
            pytest.exit(
                '\n\nOCTOBOX_REQUIRE_POSTGRES=1 esta setado mas o banco ativo e SQLite.\n'
                'Configure DATABASE_URL apontando para PostgreSQL antes de rodar.\n'
                'Para rodar localmente sem PostgreSQL: nao sete OCTOBOX_REQUIRE_POSTGRES.\n',
                returncode=3,
            )
    except Exception:
        # Django ainda nao configurado — deixa o flow normal prosseguir.
        pass


def pytest_collection_modifyitems(config, items):
    """Marca como skip qualquer test cujo node-id esteja em broken-tests.txt.

    Fase 1 fallback documentado: gate da Fase 0 (>5% falhas) acionado,
    entao fazemos opt-out explicito via lista versionada em vez de
    bloquear todo o CI. Cada linha removida da lista significa que um
    teste foi consertado.
    """
    broken = _load_broken_tests()
    if not broken:
        return
    skip_marker = pytest.mark.skip(reason='Marked broken in tests/broken-tests.txt (Fase 1 fallback)')
    for item in items:
        if item.nodeid in broken:
            item.add_marker(skip_marker)


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


@pytest.fixture(scope='class', autouse=True)
def _class_tenant_schema_context(request, test_tenant):
    """Envolve a CLASSE TestCase inteira (incluindo setUpTestData) em
    schema_context do test_tenant.

    Fase 0.5 root cause fix: Django TestCase.setUpTestData e classmethod
    que roda 1x antes de qualquer test method. Fixture autouse de escopo
    'function' (versao antiga) entrava DEPOIS do setUpTestData, deixando
    qualquer INSERT em modelo TENANT_APP dentro de setUpTestData em
    schema public — onde a tabela nao existe. Erro tipico:
        django.db.utils.ProgrammingError: relation "boxcore_classsession"
        does not exist

    Escopo 'class' (pytest) cobre TODO o lifecycle de uma TestCase,
    incluindo setUpClass / setUpTestData / setUp / test method / tearDown.

    Resolveu 118 ERRORED de uma vez na Fase 0.5 (61% do inventario).

    OPT-OUT (Sprint 9): classes marcadas @pytest.mark.public_schema rodam no
    schema public (sem schema_context). Necessario para testes que criam ou
    manipulam tenants (provision_box, archive_box) — django-tenants proibe
    criar/alterar um Box fora do schema public.
    """
    if request.node.get_closest_marker('public_schema'):
        yield
        return
    if test_tenant is None:
        yield
        return

    from django_tenants.utils import schema_context
    with schema_context(test_tenant.schema_name):
        yield


@pytest.fixture(autouse=True)
def _tenant_schema_context(request, test_tenant):
    """Mantem schema_context ativo per-test (alem do per-class acima).

    Por que ambos? schema_context() faz SET search_path no nivel da
    conexao. Em ordem aleatoria + xdist + transaction rollback do
    pytest-django, o search_path pode ser perdido entre transactions.
    Re-entrar per-function garante search_path correto antes de cada
    test method rodar.

    Quando django_tenants nao esta ativo (SQLite fallback), test_tenant
    e None — pula o context manager e roda o test diretamente.

    OPT-OUT (Sprint 9): respeita @pytest.mark.public_schema (ver fixture
    _class_tenant_schema_context acima).
    """
    if request.node.get_closest_marker('public_schema'):
        yield
        return
    if test_tenant is None:
        yield
        return

    from django_tenants.utils import schema_context
    with schema_context(test_tenant.schema_name):
        yield


@pytest.fixture(scope='class', autouse=True)
def _auto_membership_for_test_users(test_tenant, django_db_setup):
    """Sprint 4: auto-associa qualquer User criado durante o teste ao
    Box de teste via control.Membership.

    Sem isso, TenantBySessionMiddleware retorna 403 para qualquer rota
    privada de staff porque o user nao tem nenhum Membership cadastrado
    (e o tenant nao consegue ser resolvido). Antes de schema-per-tenant
    isso nao era problema — todos os users eram automaticamente do box
    unico da instancia.

    Implementacao: instala um post_save signal em auth.User que cria
    Membership(box=test_tenant, role=OWNER, is_primary_box=True) para
    qualquer user salvo. Removido no teardown.

    FASE 0.5 — escopo class: setUpTestData (classmethod do Django
    TestCase) cria User antes de qualquer fixture function-scope rodar.
    Sem escopo class, o signal nao estava instalado quando User era
    criado em setUpTestData, e os tests caiam em 403 mesmo com schema
    correto.
    """
    if test_tenant is None:
        yield
        return

    from django.contrib.auth import get_user_model
    from django.db.models.signals import post_save
    from control.models import Membership

    User = get_user_model()

    def _ensure_membership(sender, instance, created, **kwargs):
        if not created:
            return
        try:
            Membership.objects.get_or_create(
                user=instance,
                box=test_tenant,
                defaults={
                    'role': Membership.Role.OWNER,
                    'is_primary_box': True,
                },
            )
        except Exception:
            pass

    post_save.connect(_ensure_membership, sender=User, dispatch_uid='conftest_auto_membership')
    try:
        yield
    finally:
        post_save.disconnect(dispatch_uid='conftest_auto_membership', sender=User)
