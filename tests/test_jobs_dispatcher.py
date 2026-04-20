"""
ARQUIVO: testes do dispatcher oficial de jobs.

POR QUE ELE EXISTE:
- protege o corredor central entre `job_type` e task concreta.
"""

from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from jobs.dispatcher import (
    build_dispatch_context,
    dispatch_async_job,
    get_registered_job,
)


class JobsDispatcherTests(SimpleTestCase):
    def test_build_dispatch_context_keeps_mesh_payload(self):
        context = build_dispatch_context(
            job_type='student_import_csv',
            file_path='C:\\temp\\students.csv',
            actor_id=7,
            signal_envelope={'correlation_id': 'corr-1'},
        )

        self.assertEqual(context['job_type'], 'student_import_csv')
        self.assertEqual(context['file_path'], 'C:\\temp\\students.csv')
        self.assertEqual(context['actor_id'], 7)
        self.assertEqual(context['signal_envelope']['correlation_id'], 'corr-1')

    def test_get_registered_job_returns_known_job(self):
        registered_job = get_registered_job('student_import_csv')

        self.assertIsNotNone(registered_job)
        self.assertEqual(registered_job.source_channel, 'operations.student_import')

    def test_get_registered_job_returns_project_knowledge_reindex(self):
        registered_job = get_registered_job('project_knowledge_reindex')

        self.assertIsNotNone(registered_job)
        self.assertEqual(registered_job.source_channel, 'knowledge.reindex')

    @patch('operations.tasks.run_csv_student_import_job.delay')
    def test_dispatch_async_job_routes_to_registered_task(self, delay_mock):
        delay_mock.return_value = SimpleNamespace(id='task-123')
        job = SimpleNamespace(id=19)

        task = dispatch_async_job(
            job=job,
            dispatch_context=build_dispatch_context(
                job_type='student_import_csv',
                file_path='C:\\temp\\students.csv',
                actor_id=7,
                signal_envelope={'correlation_id': 'corr-1'},
            ),
        )

        self.assertEqual(task.id, 'task-123')
        delay_kwargs = delay_mock.call_args.kwargs
        self.assertEqual(delay_kwargs['job_id'], 19)
        self.assertEqual(delay_kwargs['signal_envelope']['correlation_id'], 'corr-1')

    @patch('knowledge.tasks.run_project_knowledge_reindex.delay')
    def test_dispatch_async_job_routes_to_project_knowledge_task(self, delay_mock):
        delay_mock.return_value = SimpleNamespace(id='task-rag-1')
        job = SimpleNamespace(id=33)

        task = dispatch_async_job(
            job=job,
            dispatch_context=build_dispatch_context(
                job_type='project_knowledge_reindex',
                actor_id=7,
                signal_envelope={'correlation_id': 'corr-rag-1'},
                payload={'force': True, 'with_embeddings': True},
            ),
        )

        self.assertEqual(task.id, 'task-rag-1')
        delay_kwargs = delay_mock.call_args.kwargs
        self.assertEqual(delay_kwargs['job_id'], 33)
        self.assertTrue(delay_kwargs['force'])
        self.assertTrue(delay_kwargs['with_embeddings'])
