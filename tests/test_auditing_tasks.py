from contextlib import contextmanager
from unittest.mock import patch

from django.test import SimpleTestCase

from auditing.tasks import async_log_audit_event


def _run_task(*args, **kwargs):
    runner = getattr(async_log_audit_event, 'run', async_log_audit_event)
    return runner(*args, **kwargs)


class AuditEventTaskTenantScopeTests(SimpleTestCase):
    def test_rejects_legacy_unscoped_or_invalid_payload_before_writer(self):
        with patch('auditing.services._write_audit_event') as writer:
            for tenant_schema in (None, '', 'public', 'box_bad/schema'):
                with self.subTest(tenant_schema=tenant_schema):
                    with self.assertRaisesRegex(ValueError, 'tenant-schema-required'):
                        _run_task({'action': 'student.updated'}, tenant_schema=tenant_schema)

            with self.assertRaisesRegex(ValueError, 'tenant-schema-mismatch'):
                _run_task(
                    {'action': 'student.updated', 'tenant_schema': 'box_a'},
                    tenant_schema='box_b',
                )
            with self.assertRaisesRegex(ValueError, 'audit-payload-invalid'):
                _run_task(
                    {'action': 'student.updated', 'unexpected': 'value'},
                    tenant_schema='box_a',
                )

        writer.assert_not_called()

    def test_delegates_to_common_writer_inside_explicit_tenant_fence(self):
        events = []

        @contextmanager
        def context_scope(kind, schema_name):
            events.append((kind, 'enter', schema_name))
            yield
            events.append((kind, 'exit', schema_name))

        def schema_context_mock(schema_name):
            return context_scope('schema', schema_name)

        def tenant_write_guard_mock(schema_name):
            return context_scope('fence', schema_name)

        def writer_mock(**kwargs):
            events.append(('writer', kwargs))
            return True

        payload = {
            'tenant_schema': 'box_test',
            'actor_id': 7,
            'action': 'student.updated',
            'target_model': 'boxcore.student',
            'target_id': 42,
            'target_label': 'Pessoa <aluno@example.invalid>',
            'description': 'Dados do aluno atualizados.',
            'metadata': {'email': 'aluno@example.invalid'},
        }

        with (
            patch('django_tenants.utils.schema_context', side_effect=schema_context_mock),
            patch('control.tenant_write_fence.tenant_write_guard', side_effect=tenant_write_guard_mock),
            patch('auditing.services._write_audit_event', side_effect=writer_mock) as writer,
        ):
            result = _run_task(payload)

        self.assertTrue(result)
        self.assertEqual(events[0], ('schema', 'enter', 'box_test'))
        self.assertEqual(events[1], ('fence', 'enter', 'box_test'))
        self.assertEqual(events[2][0], 'writer')
        self.assertEqual(events[3], ('fence', 'exit', 'box_test'))
        self.assertEqual(events[4], ('schema', 'exit', 'box_test'))
        writer.assert_called_once_with(
            actor_id=7,
            action='student.updated',
            target_model='boxcore.student',
            target_id='42',
            target_label='student',
            description='Dados do aluno atualizados.',
            metadata={'email': 'aluno@example.invalid'},
        )

    def test_reports_common_writer_failure_without_claiming_success(self):
        from contextlib import nullcontext

        payload = {'tenant_schema': 'box_test', 'action': 'student.updated'}
        with (
            patch('django_tenants.utils.schema_context', return_value=nullcontext()),
            patch('control.tenant_write_fence.tenant_write_guard', return_value=nullcontext()),
            patch('auditing.services._write_audit_event', return_value=False),
        ):
            result = _run_task(payload)

        self.assertFalse(result)

    def test_fence_failure_does_not_escape_tenant_schema_in_task_error(self):
        from contextlib import nullcontext

        from control.tenant_write_fence import TenantWritesFrozen

        @contextmanager
        def frozen_guard(schema_name):
            raise TenantWritesFrozen(schema_name, 'restore-window')
            yield

        payload = {'tenant_schema': 'box_secret', 'action': 'student.updated'}
        with (
            patch('django_tenants.utils.schema_context', return_value=nullcontext()),
            patch('control.tenant_write_fence.tenant_write_guard', side_effect=frozen_guard),
            patch('auditing.services._write_audit_event') as writer,
        ):
            with self.assertRaisesRegex(RuntimeError, 'async_audit_event_write_failed') as raised:
                _run_task(payload)

        self.assertNotIn('box_secret', str(raised.exception))
        writer.assert_not_called()
