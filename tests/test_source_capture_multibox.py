"""
ARQUIVO: gate de saída da Onda 6 — token de source-capture com N boxes ATIVOS.
docs/plans/ondas-correcao-tenancy-billing-2026-08-25.md, ver ADR-014.

POR QUE EXISTE:
- Prova o único ponto da Onda 6 que precisava de código real: o link público
  de qualificação de origem (/alunos/origem/qualificar/) resolvia tenant só
  via SINGLE_ACTIVE_BOX — quebra no instante em que existir um segundo Box
  ATIVO (retorna None/ambíguo, a rota vira 404 para todo mundo, mesmo com
  token válido). Com box_root_slug embutido no token, o link continua
  funcionando com N boxes ativos simultaneamente.
- Cobre também compatibilidade retroativa: tokens emitidos ANTES desta
  mudança (sem box_root_slug, até 30 dias em voo) continuam funcionando
  enquanto valer o fallback pilot (1 box ativo), e falham graciosamente
  (404, não 500) quando não dá mais para desambiguar.

@pytest.mark.public_schema: precisa criar um SEGUNDO Box — django-tenants
exige que criação de tenant rode em schema public (mesmo padrão de
access/tests/test_access_boundary.py e tests/test_control_services.py).

REQUISITO DE EXECUÇÃO (mesmo aviso que já vale para tests/test_tenant_boundary.py):
o schema novo só ganha as tabelas TENANT_APPS de verdade rodando com
`--create-db --migrations` (override do `--reuse-db --nomigrations` padrão
de pytest.ini — ver docstring de conftest.py). Sob o padrão, `migrate_schemas`
não cria `boxcore_student` no schema recém-criado — setUp detecta isso e
skipa a classe inteira, em vez de falhar com ProgrammingError.

BUG REAL ACHADO EM CI (não local): a primeira versão deste arquivo rodava
`call_command('migrate_schemas', ...)` dentro de `TestCase.setUp()` — ou
seja, DENTRO do atomic() que TestCase já abre por padrão. Localmente
(processo único, sem xdist) isso não dava sinal de erro visível. Sob
`-n 4` (pytest-xdist, 4 workers paralelos, é assim que o CI roda) a DDL
real de `migrate_schemas` corrompia a conexão compartilhada do worker —
TODO teste agendado para aquele worker pelo resto da run falhava com
`psycopg.OperationalError: the connection is closed`, em cascata, em
arquivos completamente não relacionados a este. Reproduzido em 2 dos 3
seeds do order-dependence-check e no full-test-suite.

Fix: migrar o schema UMA VEZ por sessão, fora de qualquer transação de
teste, via `django_db_blocker.unblock()` — o MESMO padrão que o fixture
`test_tenant` já usa em conftest.py para o box_test. `_inject_box_b`
injeta o resultado na instância da TestCase (pytest-django suporta
fixtures pytest dentro de unittest.TestCase via método autouse).
"""

import pytest
from django.contrib.auth import get_user_model
from django.db import connection as db_connection
from django.test import TestCase
from django.urls import reverse
from django_tenants.utils import schema_context

from control.models import Box
from students.infrastructure.source_capture_links import build_student_source_capture_token
from tests.factories import StudentFactory


def _table_exists(schema_name: str, table_name: str) -> bool:
    with db_connection.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
            [schema_name, table_name],
        )
        return cur.fetchone() is not None


@pytest.fixture(scope='session')
def _source_capture_box_b(django_db_setup, django_db_blocker):
    """Segundo Box + schema migrado de verdade, criado UMA VEZ por sessão,
    fora do atomic() de qualquer TestCase — ver "BUG REAL ACHADO EM CI"
    acima. Idempotente via get_or_create, mesmo padrão do fixture
    test_tenant em conftest.py."""
    from django.core.management import call_command

    with django_db_blocker.unblock():
        owner, _ = get_user_model().objects.get_or_create(
            username='__pytest_source_capture_box_b_owner__',
            defaults={'email': '__pytest_box_b__@example.test'},
        )
        box, _created = Box.objects.get_or_create(
            slug='box-b-source-capture',
            defaults={
                'schema_name': 'box_b_source_capture',
                'display_name': 'Box B (source capture)',
                'status': Box.Status.ACTIVE,
                'owner_user': owner,
            },
        )
        with db_connection.cursor() as cur:
            cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{box.schema_name}"')
        call_command('migrate_schemas', schema=box.schema_name, verbosity=0, interactive=False)

    return box


@pytest.mark.public_schema
class SourceCaptureTokenMultiBoxTests(TestCase):
    @pytest.fixture(autouse=True)
    def _inject_box_b(self, _source_capture_box_b):
        self.box_b = _source_capture_box_b

    def setUp(self):
        self.test_tenant = Box.objects.get(slug='test')
        # Testes anteriores podem ter suspendido o box_b (ver o teste de
        # fallback abaixo) — reafirma ACTIVE a cada teste, já que o fixture
        # é session-scoped e não passa pelo rollback do TestCase.
        Box.objects.filter(pk=self.box_b.pk).update(status=Box.Status.ACTIVE)

        if not _table_exists(self.box_b.schema_name, 'boxcore_student'):
            self.skipTest(
                'boxcore_student ausente em schema recem-criado — rode com '
                '--create-db --migrations (ver docstring deste arquivo e de conftest.py).'
            )

    def test_token_with_box_root_slug_resolves_correct_box_even_with_two_active(self):
        """O caso real: link emitido no box A continua abrindo o aluno certo
        do box A, mesmo com o box B também ATIVO ao mesmo tempo — sem isso,
        SINGLE_ACTIVE_BOX sozinho devolveria None (2 boxes ativos) e a rota
        cairia em Http404 pra QUALQUER token, válido ou não."""
        with schema_context(self.test_tenant.schema_name):
            student = StudentFactory(full_name='Aluno do Box A')
            token = build_student_source_capture_token(
                student_id=student.id, box_root_slug=self.test_tenant.schema_name,
            )

        response = self.client.get(reverse('student-source-capture'), {'token': token})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Aluno do Box A')

    def test_token_resolves_box_b_specifically_not_box_a(self):
        """Contraprova de ambiguidade: o MESMO fluxo, mas o token aponta pro
        box B — prova que não é coincidência de 'primeiro box encontrado'."""
        with schema_context(self.box_b.schema_name):
            student_b = StudentFactory(full_name='Aluno do Box B')
            token_b = build_student_source_capture_token(
                student_id=student_b.id, box_root_slug=self.box_b.schema_name,
            )

        response = self.client.get(reverse('student-source-capture'), {'token': token_b})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Aluno do Box B')

    def test_legacy_token_without_box_root_slug_falls_back_when_exactly_one_active(self):
        """Compat: token emitido ANTES da Onda 6 (sem box_root_slug) — se
        eu desativar o box B, sobra exatamente 1 ATIVO e o fallback pilot
        continua funcionando, igual ao comportamento de antes desta onda."""
        Box.objects.filter(pk=self.box_b.pk).update(status=Box.Status.SUSPENDED)

        with schema_context(self.test_tenant.schema_name):
            student = StudentFactory(full_name='Aluno Token Legado')
            legacy_token = build_student_source_capture_token(student_id=student.id)  # sem box_root_slug

        response = self.client.get(reverse('student-source-capture'), {'token': legacy_token})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Aluno Token Legado')

    def test_legacy_token_without_box_root_slug_fails_gracefully_with_two_active(self):
        """Token legado + 2 boxes ativos: não dá pra desambiguar — precisa
        cair em 404 (link inválido), NUNCA em 500."""
        with schema_context(self.test_tenant.schema_name):
            student = StudentFactory(full_name='Aluno Sem Box No Token')
            legacy_token = build_student_source_capture_token(student_id=student.id)  # sem box_root_slug

        response = self.client.get(reverse('student-source-capture'), {'token': legacy_token})

        self.assertEqual(response.status_code, 404)
