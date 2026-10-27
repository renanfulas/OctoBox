from contextlib import nullcontext
from unittest.mock import patch

from django.test import SimpleTestCase

from jobs.tasks import run_due_async_job_retries


def _run_task(*args, **kwargs):
    runner = getattr(run_due_async_job_retries, 'run', run_due_async_job_retries)
    return runner(*args, **kwargs)


class JobsTaskTenantScopeTests(SimpleTestCase):
    @patch('jobs.tasks.reprocess_due_async_jobs')
    def test_rejects_missing_or_public_schema_before_reprocessing(self, reprocess_mock):
        for tenant_schema in (None, '', 'public'):
            with self.subTest(tenant_schema=tenant_schema):
                with self.assertRaisesRegex(ValueError, 'tenant-schema-required'):
                    _run_task(tenant_schema=tenant_schema)

        reprocess_mock.assert_not_called()

    @patch('django_tenants.utils.schema_context')
    @patch('control.tenant_write_fence.tenant_write_guard')
    @patch('jobs.tasks.reprocess_due_async_jobs')
    def test_reprocesses_inside_the_explicit_tenant_fence(
        self,
        reprocess_mock,
        tenant_write_guard_mock,
        schema_context_mock,
    ):
        reprocess_mock.return_value = {'dispatched_count': 2}
        tenant_write_guard_mock.return_value = nullcontext()
        schema_context_mock.return_value = nullcontext()

        result = _run_task(limit=8, tenant_schema='box_demo')

        self.assertEqual(result, {'dispatched_count': 2})
        schema_context_mock.assert_called_once_with('box_demo')
        tenant_write_guard_mock.assert_called_once_with('box_demo')
        reprocess_mock.assert_called_once_with(limit=8)
