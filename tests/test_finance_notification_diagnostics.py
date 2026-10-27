from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from finance.notification_diagnostics import build_payment_notification_diagnostics
from finance.payment_notifications import notify_payment_confirmed


class PaymentNotificationDiagnosticsTests(SimpleTestCase):
    def test_delivery_failures_keep_results_without_logging_exception_text(self):
        marker = 'PII-SENTINEL-payment-delivery'
        payment = SimpleNamespace(id=91)

        with (
            patch('finance.payment_notifications._send_confirmation_email', side_effect=RuntimeError(marker)),
            patch('finance.payment_notifications._send_confirmation_push', side_effect=RuntimeError(marker)),
            patch('finance.payment_notifications._send_confirmation_whatsapp', side_effect=RuntimeError(marker)),
            patch('finance.payment_notifications.logger.error') as error_log,
        ):
            result = notify_payment_confirmed(payment)

        self.assertEqual(result, {'email': 'error', 'push': 'error', 'whatsapp': 'error'})
        self.assertEqual(error_log.call_count, 3)
        self.assertTrue(all(marker not in repr(call) for call in error_log.call_args_list))
        self.assertEqual(
            [call.args for call in error_log.call_args_list],
            [
                ('notify_payment_confirmed_failed channel=email error_type=%s', 'RuntimeError'),
                ('notify_payment_confirmed_failed channel=push error_type=%s', 'RuntimeError'),
                ('notify_payment_confirmed_failed channel=whatsapp error_type=%s', 'RuntimeError'),
            ],
        )

    @override_settings(
        STUDENT_EMAIL_PROVIDER='resend',
        STUDENT_EMAIL_FROM='billing@example.invalid',
        STUDENT_RESEND_API_KEY='secret-api-key-for-test',
        STUDENT_WEB_PUSH_VAPID_PUBLIC_KEY='public-key',
        STUDENT_WEB_PUSH_VAPID_PRIVATE_KEY='private-key',
        STUDENT_WEB_PUSH_VAPID_CLAIMS_SUBJECT='mailto:ops@example.invalid',
    )
    def test_reports_configuration_without_credentials_or_recipient_data(self):
        diagnostics = build_payment_notification_diagnostics()
        channels = {item['key']: item for item in diagnostics['channels']}

        self.assertEqual(channels['email']['status'], 'configured')
        self.assertEqual(channels['email']['delivery_receipt']['status'], 'configuration_missing')
        self.assertEqual(
            channels['email']['delivery_receipt']['reason_code'],
            'resend_webhook_secret_missing',
        )
        self.assertEqual(channels['push']['status'], 'configured')
        self.assertEqual(channels['push']['delivery_receipt']['status'], 'not_supported')
        self.assertEqual(channels['whatsapp']['status'], 'not_implemented')
        self.assertEqual(channels['whatsapp']['delivery_receipt']['status'], 'not_implemented')
        serialized = repr(diagnostics)
        self.assertNotIn('secret-api-key-for-test', serialized)
        self.assertNotIn('private-key', serialized)
        self.assertNotIn('billing@example.invalid', serialized)
        self.assertTrue(all(item['recipient_scope'] == 'verified_per_payment' for item in channels.values()))

    @override_settings(
        STUDENT_EMAIL_PROVIDER='smtp',
        STUDENT_EMAIL_FROM='',
        EMAIL_HOST='localhost',
        STUDENT_WEB_PUSH_VAPID_PUBLIC_KEY='',
        STUDENT_WEB_PUSH_VAPID_PRIVATE_KEY='',
        STUDENT_WEB_PUSH_VAPID_CLAIMS_SUBJECT='',
    )
    def test_marks_unconfigured_channels_and_whatsapp_unavailable(self):
        diagnostics = build_payment_notification_diagnostics()
        channels = {item['key']: item for item in diagnostics['channels']}

        self.assertEqual(channels['email']['status'], 'configuration_missing')
        self.assertEqual(channels['email']['delivery_receipt']['status'], 'not_supported')
        self.assertEqual(channels['push']['reason_code'], 'push_vapid_configuration_missing')
        self.assertEqual(channels['whatsapp']['status'], 'not_implemented')

    @override_settings(
        STUDENT_EMAIL_PROVIDER='resend',
        STUDENT_EMAIL_FROM='billing@example.invalid',
        STUDENT_RESEND_API_KEY='secret-api-key-for-test',
        PAYMENT_NOTIFICATION_RESEND_WEBHOOK_SECRET='webhook-secret-for-test',
    )
    def test_secret_presence_does_not_claim_resend_endpoint_is_configured(self):
        channels = {
            item['key']: item
            for item in build_payment_notification_diagnostics()['channels']
        }

        receipt = channels['email']['delivery_receipt']
        self.assertEqual(channels['email']['status'], 'configured')
        self.assertEqual(receipt['status'], 'endpoint_unverified')
        self.assertEqual(receipt['reason_code'], 'resend_webhook_secret_present_endpoint_unverified')
        self.assertNotIn('webhook-secret-for-test', repr(channels))
