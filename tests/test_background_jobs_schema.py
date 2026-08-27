"""
ARQUIVO: teste de gate — Onda 4, Passo 2 (thread de background job herda o
schema certo).

POR QUE EXISTE:
- Threads do Python NAO herdam o schema/tenant da conexao do request — cada
  Thread tem sua propria conexao Django (thread-local). O unico caller real
  hoje (catalog/views/student_views.py::StudentImportView, via
  StudentImporter().import_from_file) escreve Student — TENANT_APP — dentro
  dessa thread. Sem capturar e reaplicar o schema, a escrita rodaria contra
  o schema default da conexao NOVA da thread, nao contra o box do cliente
  que fez upload. Bug de correcao real, descoberto ao investigar a Onda 4
  (namespace de cache por box) — nao e so questao de cache.

@pytest.mark.public_schema: o teste PRECISA controlar qual schema esta ativo
na conexao do "request" antes de chamar submit_background_job (e depois
verificar em qual schema o dado foi de fato escrito) — schema_context
explicito em vez do autouse do conftest.

LIMPEZA — duas ferramentas tentadas e descartadas antes desta:
1. addCleanup com DELETE via ORM: a linha sobrevive ao teste mesmo o DELETE
   reportando sucesso. addCleanup roda DEPOIS do tearDown/rollback (unittest.
   TestCase.run(): setUp -> teste -> tearDown -> doCleanups — confirmado lendo
   a fonte), entao nao e ordem de rollback desfazendo o delete; o mecanismo
   exato nao foi isolado, mas o resultado empirico e consistente: delete via
   ORM depois do ciclo de vida do TestCase nao persiste neste setup.
2. TransactionTestCase (a ferramenta que os docs do Django recomendam pra
   teste com threads/multiplas conexoes): quebra a limpeza via `flush`, que
   nao conhece schema de tenant e tenta rodar contra tabelas que so existem
   em box_test — "table doesn't exist" ao tentar limpar public.
Solucao: apagar via uma THREAD PROPRIA, a mesma tecnica que criou a sobra —
conexao nova, autocommit de verdade, fora de qualquer coisa que o Django
gerencia (TestCase, atomic, cleanups). thread.join() garante que termina
antes do teste seguir.
"""

from __future__ import annotations

import threading
import time

import pytest
from django.test import TestCase
from django_tenants.utils import schema_context

from shared_support.background_jobs import (
    JobStatus,
    create_job,
    get_job_status,
    submit_background_job,
)

TENANT_SCHEMA = 'box_test'


def _wait_for_terminal_status(job_id, *, timeout=5.0):
    """Poll ate o job sair de PENDING/RUNNING — mesmo contrato que um caller
    real observaria via get_job_status (nao ha thread.join() exposto)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        data = get_job_status(job_id)
        if data and data['status'] in (JobStatus.COMPLETED, JobStatus.FAILED):
            return data
        time.sleep(0.05)
    raise AssertionError(f'job {job_id} nao terminou em {timeout}s')


def _submit_and_wait(job_fn, job_id, *, timeout=5.0):
    """submit_background_job + poll, mas ALEM disso junta a thread spawnada
    antes de devolver o controle ao teste.

    Achado em CI, nao local (docs/plans/ondas-correcao-tenancy-billing-
    2026-08-25.md, bloco da Onda 4): submit_background_job nao expoe o
    objeto Thread, e _wait_for_terminal_status so espera o STATUS aparecer
    no cache — que e escrito dentro do `try`, ANTES do `finally:
    thread_connection.close()` rodar. Sob processo unico isso e uma janela
    de microsegundos, inofensiva. Sob pytest-xdist (-n 4, como o CI roda de
    verdade) com varios testes desta classe abrindo threads em sequencia
    rapida, a thread pode sobreviver ao retorno do metodo de teste com sua
    conexao Postgres ainda aberta — sob CPU/IO contencionados o suficiente,
    isso acumula conexoes penduradas entre workers e um teste COMPLETAMENTE
    nao relacionado, rodando depois, recebe psycopg.OperationalError('the
    connection is closed'). Reproduzido no CI (full-test-suite e 3/3 seeds
    do order-dependence-check), nao reproduzido localmente em processo
    unico nem sob -n 4 num run isolado deste arquivo — exatamente o
    padrao de uma corrida de recursos, nao um bug logico.

    Fix: capturar o conjunto de threads vivas ANTES de submeter, e depois
    do status virar terminal, joinar qualquer thread NOVA que tenha
    aparecido — garante que finally/close() ja rodou antes do teste (e o
    proximo) seguir.
    """
    before = set(threading.enumerate())
    submit_background_job(job_fn, job_id)
    result = _wait_for_terminal_status(job_id, timeout=timeout)
    for t in set(threading.enumerate()) - before:
        t.join(timeout=5.0)
    return result


def _delete_via_own_thread(schema, model, pks):
    """Apaga fora de qualquer transacao gerenciada pelo Django — mesma tecnica
    (conexao nova, thread propria) que criou a escrita a ser limpa. Ver
    docstring do modulo pras duas tentativas que nao funcionaram antes desta.
    """
    def _run():
        from django.db import connection as thread_connection
        try:
            with schema_context(schema):
                model.objects.filter(pk__in=pks).delete()
        finally:
            thread_connection.close()

    t = threading.Thread(target=_run)
    t.start()
    t.join(timeout=5.0)


@pytest.mark.public_schema
class BackgroundJobInheritsRequestSchemaTests(TestCase):
    def test_job_fn_writes_land_in_the_request_schema_not_public(self):
        """O caso real: job_fn cria um Student (TENANT_APP) dentro da thread.
        Sem o fix, essa escrita cairia fora do schema do box.

        Telefone com uuid: mesmo com a limpeza por thread, e uma segunda
        camada contra colisao se dois testes rodarem em paralelo (xdist) no
        mesmo schema fisico.

        Onda 4 (2026-08-26): o polling (_wait_for_terminal_status) agora
        PRECISA rodar dentro do MESMO schema_context de create_job/
        submit_background_job — desde que CACHES['default'] ganhou
        KEY_FUNCTION particionada por schema, a chave de status do job só é
        visível dentro do schema em que foi escrita. Isso não é artificial:
        numa request real, o endpoint de polling (chamado pelo JS do
        navegador) resolve o MESMO box via TenantBySessionMiddleware,
        porque é a mesma sessão do mesmo usuário — a classe é
        @pytest.mark.public_schema (ambiente ambiente fora do `with` é
        'public'), então sair do `with` antes de sondar simularia um
        usuário que trocou de box no meio do polling, cenário que não
        acontece em produção hoje (SINGLE_ACTIVE_BOX).
        """
        import uuid as uuid_module
        from students.models import Student

        unique_phone = f'5511900{uuid_module.uuid4().int % 10**6:06d}'

        with schema_context(TENANT_SCHEMA):
            job_id = create_job('test_import', total_items=1)

            created_ids = []

            def _job_fn(job_id_arg):
                student = Student.objects.create(
                    full_name='Aluno via Thread', status='active', phone=unique_phone,
                )
                created_ids.append(student.id)

            # Registrado ANTES do poll, de proposito, capturando created_ids
            # por REFERENCIA (nao list(created_ids) aqui — nesse ponto a
            # thread pode nao ter rodado ainda, entao uma copia agora seria
            # sempre []). addCleanup roda mesmo se a asserção abaixo falhar
            # (ou o poll estourar timeout) — sem isso, uma falha nesta linha
            # deixava a Student criada pela thread orfa no banco reaproveitado
            # (--reuse-db), poluindo outros testes (ja aconteceu nesta sessao:
            # ver docs/plans/ondas-correcao-tenancy-billing-2026-08-25.md,
            # bloco da Onda 4).
            self.addCleanup(lambda: _delete_via_own_thread(TENANT_SCHEMA, Student, list(created_ids)))

            result = _submit_and_wait(_job_fn, job_id)

        self.assertEqual(result['status'], JobStatus.COMPLETED)
        self.assertEqual(len(created_ids), 1)

        with schema_context(TENANT_SCHEMA):
            self.assertTrue(
                Student.objects.filter(pk=created_ids[0]).exists(),
                'Student nao foi encontrado no schema do box — a thread escreveu no lugar errado',
            )

        with schema_context('public'):
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'boxcore_student'"
                )
                self.assertIsNone(
                    cursor.fetchone(),
                    'boxcore_student existe em public — nao da pra provar isolamento por essa via '
                    '(o teste depende da tabela so existir no schema do tenant)',
                )

    def test_job_failure_still_marks_failed_within_correct_schema(self):
        """job_fn levanta — mark_job_failed roda no MESMO schema_context,
        nao vaza pra fora nem quebra por falta de tenant.

        Onda 4: polling dentro do mesmo `with` — ver docstring de
        test_job_fn_writes_land_in_the_request_schema_not_public acima.
        """
        with schema_context(TENANT_SCHEMA):
            job_id = create_job('test_import_fail', total_items=1)

            def _job_fn(job_id_arg):
                raise RuntimeError('linha invalida no CSV')

            result = _submit_and_wait(_job_fn, job_id)

        self.assertEqual(result['status'], JobStatus.FAILED)
        self.assertIn('linha invalida', result['error_message'])

    def test_job_called_from_public_schema_does_not_crash(self):
        """Chamador em schema public (ex.: webhook, management command) —
        schema_context('public') e valido e inofensivo, thread completa
        normalmente. Cobre o branch quando connection.schema_name nao e um
        schema de tenant."""
        job_id = create_job('test_public_schema', total_items=1)
        calls = []

        def _job_fn(job_id_arg):
            calls.append(job_id_arg)

        result = _submit_and_wait(_job_fn, job_id)  # ambiente do teste ja esta em public
        self.assertEqual(result['status'], JobStatus.COMPLETED)
        self.assertEqual(calls, [job_id])
