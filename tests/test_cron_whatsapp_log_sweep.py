from contextlib import nullcontext
from io import StringIO
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.test import TestCase


class WhatsAppLogSweepCommandTests(TestCase):
    @patch('communications.management.commands.cron_whatsapp_log_sweep.WhatsAppMessageLog.objects.filter')
    @patch('communications.management.commands.cron_whatsapp_log_sweep.Box.objects.filter')
    @patch('communications.management.commands.cron_whatsapp_log_sweep.schema_context')
    def test_default_mode_is_tenant_scoped_dry_run(
        self, schema_context, box_filter, log_filter,
    ):
        schema_context.return_value = nullcontext()
        box = Mock(schema_name='box_private', pk=12)
        box_filter.return_value.only.return_value.first.return_value = box
        log_filter.return_value.count.return_value = 3
        output = StringIO()

        call_command('cron_whatsapp_log_sweep', schema='box_private', stdout=output)

        box_filter.assert_called_once()
        log_filter.assert_called_once()
        log_filter.return_value.delete.assert_not_called()
        self.assertIn('Dry-run: 3 log(s)', output.getvalue())
        self.assertNotIn('box_private', output.getvalue())

    @patch('control.tenant_write_fence.tenant_write_guard', return_value=nullcontext())
    @patch('communications.management.commands.cron_whatsapp_log_sweep.transaction.atomic', return_value=nullcontext())
    @patch('communications.management.commands.cron_whatsapp_log_sweep.WhatsAppMessageLog.objects.filter')
    @patch('communications.management.commands.cron_whatsapp_log_sweep.Box.objects.filter')
    @patch('communications.management.commands.cron_whatsapp_log_sweep.schema_context')
    def test_apply_deletes_only_inside_explicit_tenant_and_logs_reference(
        self, schema_context, box_filter, log_filter, atomic, _write_guard,
    ):
        schema_context.return_value = nullcontext()
        box = Mock(schema_name='box_private', pk=12)
        box_filter.return_value.only.return_value.first.return_value = box
        queryset = Mock()
        queryset.count.return_value = 3
        queryset.delete.return_value = (2, {'communications.WhatsAppMessageLog': 2})
        log_filter.return_value = queryset
        output = StringIO()

        with self.assertLogs('octobox.security.gc', level='INFO') as captured:
            call_command('cron_whatsapp_log_sweep', schema='box_private', apply=True, stdout=output)

        self.assertEqual(log_filter.call_count, 1)
        queryset.delete.assert_called_once_with()
        atomic.assert_called_once_with()
        _write_guard.assert_called_once_with('box_private')
        rendered = '\n'.join(captured.output) + output.getvalue()
        self.assertNotIn('box_private', rendered)
        self.assertRegex(captured.records[0].box_ref, r'^tenant:[0-9a-f]{16}$')
