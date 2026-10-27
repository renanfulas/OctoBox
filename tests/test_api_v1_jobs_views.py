"""
ARQUIVO: testes da borda de jobs da API v1.

POR QUE ELE EXISTE:
- protege correlation id e SignalEnvelope no despacho de jobs assincronos.
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, SimpleTestCase

from api.v1.jobs_views import AsyncImportJobStatusView, AsyncImportJobView
from control.tenant_write_fence import TenantWritesFrozen


class ApiV1JobsViewsTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = SimpleNamespace(id=7, pk=7, is_authenticated=True)

    @patch('api.v1.jobs_views.tenant_write_guard')
    @patch('access.permissions.mixins.get_user_role')
    @patch('api.v1.jobs_views.get_alert_siren_defense_policy')
    @patch('api.v1.jobs_views.dispatch_async_job')
    @patch('api.v1.jobs_views.AsyncJob.objects.create')
    @patch('api.v1.jobs_views._persist_upload_to_tempfile')
    @patch('api.v1.jobs_views.build_correlation_id')
    def test_async_import_job_view_dispatches_signal_envelope(
        self,
        build_correlation_id_mock,
        persist_upload_mock,
        async_job_create_mock,
        dispatch_async_job_mock,
        get_alert_siren_defense_policy_mock,
        get_user_role_mock,
        tenant_write_guard_mock,
    ):
        get_user_role_mock.return_value = SimpleNamespace(slug='Owner')
        get_alert_siren_defense_policy_mock.return_value = {
            'level': 'silent',
            'pause_non_essential_job_submissions': False,
        }
        build_correlation_id_mock.return_value = 'corr-job-1'
        persist_upload_mock.return_value = 'C:\\temp\\octobox_import_1.csv'
        async_job_create_mock.return_value = SimpleNamespace(id=19)
        dispatch_async_job_mock.return_value = SimpleNamespace(id='task-123')
        uploaded_file = SimpleUploadedFile('students.csv', b'name\nRenan\n', content_type='text/csv')
        request = self.factory.post(
            '/api/v1/jobs/import/',
            data={'file': uploaded_file},
            HTTP_X_CORRELATION_ID='req-1',
            HTTP_X_IDEMPOTENCY_KEY='idem-1',
        )
        request.user = self.user
        request.tenant = SimpleNamespace(schema_name='box_demo')

        response = AsyncImportJobView.as_view()(request)

        self.assertEqual(response.status_code, 202)
        payload = json.loads(response.content)
        self.assertEqual(payload['correlation_id'], 'corr-job-1')
        self.assertEqual(response['X-OctoBox-Correlation-Id'], 'corr-job-1')
        async_job_create_mock.assert_called_once()
        create_kwargs = async_job_create_mock.call_args.kwargs
        self.assertEqual(create_kwargs['result']['signal_envelope']['correlation_id'], 'corr-job-1')
        self.assertEqual(create_kwargs['result']['signal_envelope']['idempotency_key'], 'idem-1')
        self.assertEqual(
            create_kwargs['result']['signal_envelope']['raw_reference'],
            'upload:students.csv',
        )
        self.assertEqual(create_kwargs['result']['dispatch_context']['job_type'], 'student_import_csv')
        self.assertEqual(create_kwargs['result']['dispatch_context']['tenant_schema'], 'box_demo')
        dispatch_kwargs = dispatch_async_job_mock.call_args.kwargs
        self.assertEqual(dispatch_kwargs['dispatch_context']['signal_envelope']['correlation_id'], 'corr-job-1')
        self.assertEqual(dispatch_kwargs['dispatch_context']['signal_envelope']['idempotency_key'], 'idem-1')
        tenant_write_guard_mock.assert_called_once_with('box_demo')

    @patch('access.permissions.mixins.get_user_role')
    @patch('api.v1.jobs_views.get_alert_siren_defense_policy')
    @patch('api.v1.jobs_views.build_correlation_id')
    def test_async_import_job_view_blocks_non_essential_import_when_alert_siren_is_high(
        self,
        build_correlation_id_mock,
        get_alert_siren_defense_policy_mock,
        get_user_role_mock,
    ):
        get_user_role_mock.return_value = SimpleNamespace(slug='Owner')
        build_correlation_id_mock.return_value = 'corr-job-contained'
        get_alert_siren_defense_policy_mock.return_value = {
            'level': 'high',
            'pause_non_essential_job_submissions': True,
        }
        uploaded_file = SimpleUploadedFile('students.csv', b'name\nRenan\n', content_type='text/csv')
        request = self.factory.post('/api/v1/jobs/import/', data={'file': uploaded_file})
        request.user = self.user

        response = AsyncImportJobView.as_view()(request)

        self.assertEqual(response.status_code, 503)
        payload = json.loads(response.content)
        self.assertEqual(payload['error'], 'alert_siren_containment')
        self.assertEqual(payload['alert_siren_level'], 'high')

    @patch('access.permissions.mixins.get_user_role')
    @patch('api.v1.jobs_views.get_alert_siren_defense_policy')
    @patch('api.v1.jobs_views._persist_upload_to_tempfile')
    @patch('api.v1.jobs_views.AsyncJob.objects.create')
    def test_async_import_job_requires_tenant_before_persisting_or_creating_job(
        self,
        async_job_create_mock,
        persist_upload_mock,
        get_alert_siren_defense_policy_mock,
        get_user_role_mock,
    ):
        get_user_role_mock.return_value = SimpleNamespace(slug='Owner')
        get_alert_siren_defense_policy_mock.return_value = {
            'level': 'silent',
            'pause_non_essential_job_submissions': False,
        }
        uploaded_file = SimpleUploadedFile('students.csv', b'name\nRenan\n', content_type='text/csv')
        request = self.factory.post('/api/v1/jobs/import/', data={'file': uploaded_file})
        request.user = self.user

        response = AsyncImportJobView.as_view()(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)['error'], 'tenant_context_required')
        persist_upload_mock.assert_not_called()
        async_job_create_mock.assert_not_called()

    def test_frozen_tenant_does_not_materialize_upload_or_create_job(self):
        with patch('access.permissions.mixins.get_user_role', return_value=SimpleNamespace(slug='Owner')):
            with patch(
                'api.v1.jobs_views.get_alert_siren_defense_policy',
                return_value={
                    'level': 'silent',
                    'pause_non_essential_job_submissions': False,
                },
            ):
                with patch(
                    'api.v1.jobs_views.tenant_write_guard',
                    side_effect=TenantWritesFrozen('box_demo'),
                ):
                    with patch('api.v1.jobs_views._persist_upload_to_tempfile') as persist_upload_mock:
                        with patch('api.v1.jobs_views.AsyncJob.objects.create') as async_job_create_mock:
                            uploaded_file = SimpleUploadedFile(
                                'students.csv',
                                b'name\nRenan\n',
                                content_type='text/csv',
                            )
                            request = self.factory.post(
                                '/api/v1/jobs/import/',
                                data={'file': uploaded_file},
                            )
                            request.user = self.user
                            request.tenant = SimpleNamespace(schema_name='box_demo')

                            response = AsyncImportJobView.as_view()(request)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(json.loads(response.content)['error'], 'tenant_write_frozen')
        persist_upload_mock.assert_not_called()
        async_job_create_mock.assert_not_called()

    @patch('access.permissions.mixins.get_user_role')
    @patch('api.v1.jobs_views.AsyncJob.objects.filter')
    @patch('api.v1.jobs_views.build_correlation_id')
    def test_async_import_job_status_view_returns_real_job_tracking(
        self,
        build_correlation_id_mock,
        async_job_filter_mock,
        get_user_role_mock,
    ):
        get_user_role_mock.return_value = SimpleNamespace(slug='Owner')
        build_correlation_id_mock.return_value = 'corr-job-2'
        async_job_filter_mock.return_value.first.return_value = SimpleNamespace(
            id=21,
            job_type='student_import_csv',
            status='pending',
            attempts=1,
            max_retries=3,
            next_retry_at=None,
            last_failure_kind='retryable',
            result={'retry_action': 'retry'},
            error='',
        )
        request = self.factory.get('/api/v1/jobs/21/status/', HTTP_X_CORRELATION_ID='req-2')
        request.user = self.user

        response = AsyncImportJobStatusView.as_view()(request, task_id='21')

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertEqual(payload['job_id'], 21)
        self.assertEqual(payload['status'], 'pending')
        self.assertEqual(payload['attempts'], 1)
        self.assertEqual(payload['result']['retry_action'], 'retry')
