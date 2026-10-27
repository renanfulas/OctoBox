from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import base64
import hashlib
import hmac
import json
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.db import close_old_connections
from django.db import transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django_tenants.utils import schema_context

from finance.models import PaymentNotificationDelivery, PaymentNotificationDeliveryStatus, PaymentStatus
from finance.notification_outbox import (
    claim_due_payment_notification_deliveries,
    dispatch_claimed_payment_notification_delivery,
    run_due_payment_notification_deliveries,
    _finalize_claim,
)
from finance.notification_webhooks import process_resend_payment_notification_webhook
from finance.notification_status import build_payment_notification_operations_snapshot
from finance.application.commands import ReconcilePaymentCommand
from finance.application.use_cases import execute_reconcile_payment_use_case
from student_identity.delivery_gateways import StudentEmailDeliveryResult
from student_identity.models import (
    StudentIdentity,
    StudentIdentityProvider,
    StudentIdentityStatus,
    StudentPushSubscription,
)
from student_identity.resend_webhooks import ResendWebhookHeaders
from control.models import Box
from tests.factories import PaymentFactory, StudentFactory, UserFactory


TENANT_SCHEMA = 'box_test'


def _resend_headers(*, event_id, event_time, payload):
    timestamp = str(int(event_time.timestamp()))
    signed = b'.'.join([event_id.encode(), timestamp.encode(), payload])
    signature = base64.b64encode(
        hmac.new(b'test_secret', signed, hashlib.sha256).digest(),
    ).decode()
    return ResendWebhookHeaders(
        webhook_id=event_id,
        timestamp=timestamp,
        signature=f'v1,{signature}',
    )


@pytest.mark.public_schema
class PaymentNotificationOutboxTests(TestCase):
    def _ensure_active_box_registry(self):
        with schema_context('public'):
            if not Box.objects.filter(schema_name=TENANT_SCHEMA).exists():
                Box.objects.create(
                    slug='payment-notification-test',
                    schema_name=TENANT_SCHEMA,
                    display_name='Payment notification test',
                    status=Box.Status.ACTIVE,
                    owner_user=UserFactory(),
                )

    def _create_due_email(self):
        with schema_context(TENANT_SCHEMA):
            student = StudentFactory(email='learner@example.test')
            payment = PaymentFactory(student=student, amount=Decimal('149.90'), status=PaymentStatus.PAID)
            delivery = PaymentNotificationDelivery.objects.create(
                payment=payment,
                logical_event_key=f'payment-confirmed:v1:{payment.pk}',
                channel='email',
                recipient_key=f'student:{student.pk}',
            )
            return payment.pk, delivery.pk

    def test_revoked_push_subscription_is_skipped_without_calling_provider(self):
        from finance.notification_outbox import enqueue_payment_confirmation

        with schema_context(TENANT_SCHEMA):
            student = StudentFactory(email='')
            payment = PaymentFactory(student=student, status=PaymentStatus.PAID)
            identity = StudentIdentity.objects.create(
                student_id=student.pk,
                box_root_slug=TENANT_SCHEMA,
                primary_box_root_slug=TENANT_SCHEMA,
                provider=StudentIdentityProvider.GOOGLE,
                provider_subject=f'push-revoked-{student.pk}',
                email='push-test@example.test',
                status=StudentIdentityStatus.ACTIVE,
            )
            subscription = StudentPushSubscription.objects.create(
                identity=identity,
                box_root_slug=TENANT_SCHEMA,
                endpoint=f'https://push.example/revoked-{student.pk}',
                subscription={'endpoint': 'https://push.example/test', 'keys': {}},
            )
            with transaction.atomic():
                enqueue_payment_confirmation(payment)
            delivery = PaymentNotificationDelivery.objects.get(
                logical_event_key=f'payment-confirmed:v1:{payment.pk}',
                channel='push',
            )

            subscription.mark_revoked(error_message='provider revoked subscription')
            subscription.save(update_fields=['revoked_at', 'last_error_at', 'last_error_message', 'updated_at'])
            delivery_id, lease_token = claim_due_payment_notification_deliveries(limit=5)[0]

            with patch('finance.notification_outbox._push_is_configured', return_value=True), patch(
                'student_identity.push_notifications.send_student_web_push_notification'
            ) as send_push:
                result = dispatch_claimed_payment_notification_delivery(
                    delivery_id=delivery_id,
                    lease_token=lease_token,
                )

            delivery.refresh_from_db()

        self.assertEqual(result, PaymentNotificationDeliveryStatus.SKIPPED)
        self.assertEqual(delivery.status, PaymentNotificationDeliveryStatus.SKIPPED)
        self.assertEqual(delivery.reason_code, 'push_subscription_unavailable')
        send_push.assert_not_called()

    @override_settings(PAYMENT_NOTIFICATION_RESEND_WEBHOOK_SECRET='whsec_test_secret')
    def test_resend_delivery_webhook_is_idempotent_and_reconciles_out_of_order_events(self):
        from finance.models import PaymentNotificationDeliveryEvent

        self._ensure_active_box_registry()
        _payment_id, delivery_id = self._create_due_email()
        event_time = timezone.now().replace(microsecond=0)
        with schema_context(TENANT_SCHEMA):
            delivery = PaymentNotificationDelivery.objects.get(pk=delivery_id)
            delivery.status = PaymentNotificationDeliveryStatus.LEASED
            delivery.lease_token = uuid4()
            delivery.lease_expires_at = event_time + timedelta(minutes=5)
            delivery.save(update_fields=['status', 'lease_token', 'lease_expires_at', 'updated_at'])
            lease_token = delivery.lease_token

        tags = {'octobox_box': TENANT_SCHEMA, 'octobox_delivery': str(delivery_id)}
        delivered_payload = json.dumps({
            'type': 'email.delivered',
            'created_at': event_time.isoformat(),
            'data': {'email_id': 'resend-email-123', 'tags': tags},
        }).encode('utf-8')
        delivered_headers = _resend_headers(
            event_id='evt_resend_delivered', event_time=event_time, payload=delivered_payload,
        )
        endpoint = reverse('api-v1-resend-payment-notifications-webhook')
        result = self.client.post(
            endpoint,
            data=delivered_payload,
            content_type='application/json',
            HTTP_SVIX_ID=delivered_headers.webhook_id,
            HTTP_SVIX_TIMESTAMP=delivered_headers.timestamp,
            HTTP_SVIX_SIGNATURE=delivered_headers.signature,
        )
        duplicate = self.client.post(
            endpoint,
            data=delivered_payload,
            content_type='application/json',
            HTTP_SVIX_ID=delivered_headers.webhook_id,
            HTTP_SVIX_TIMESTAMP=delivered_headers.timestamp,
            HTTP_SVIX_SIGNATURE=delivered_headers.signature,
        )
        self.assertEqual(result.status_code, 200)
        self.assertEqual(duplicate.status_code, 200)

        with schema_context(TENANT_SCHEMA):
            delivery = PaymentNotificationDelivery.objects.get(pk=delivery_id)
            self.assertEqual(delivery.status, PaymentNotificationDeliveryStatus.DELIVERED)
            self.assertEqual(delivery.provider_message_id, 'resend-email-123')
            self.assertIsNone(delivery.lease_token)
            self.assertEqual(PaymentNotificationDeliveryEvent.objects.filter(delivery_id=delivery_id).count(), 1)
            late_sent_payload = json.dumps({
                'type': 'email.sent',
                'created_at': (event_time - timedelta(seconds=5)).isoformat(),
                'data': {'email_id': 'resend-email-123', 'tags': tags},
            }).encode('utf-8')
            late_sent_headers = _resend_headers(
                event_id='evt_resend_sent_old', event_time=event_time, payload=late_sent_payload,
            )
            late_sent = self.client.post(
                endpoint,
                data=late_sent_payload,
                content_type='application/json',
                HTTP_SVIX_ID=late_sent_headers.webhook_id,
                HTTP_SVIX_TIMESTAMP=late_sent_headers.timestamp,
                HTTP_SVIX_SIGNATURE=late_sent_headers.signature,
            )
            self.assertEqual(late_sent.status_code, 200)
            delivery.refresh_from_db()
            self.assertEqual(delivery.status, PaymentNotificationDeliveryStatus.DELIVERED)
            self.assertEqual(PaymentNotificationDeliveryEvent.objects.filter(delivery_id=delivery_id).count(), 2)
            late_worker = _finalize_claim(
                delivery_id,
                lease_token,
                status=PaymentNotificationDeliveryStatus.PROVIDER_ACCEPTED,
                reason='',
                provider='resend',
                provider_message_id='resend-email-123',
                now=event_time,
            )

        self.assertEqual(result.json()['reason'], 'processed')
        self.assertEqual(duplicate.json()['reason'], 'duplicate-event')
        self.assertEqual(late_sent.json()['reason'], 'out-of-order-event-recorded')
        self.assertEqual(late_worker, 'lease_lost')

    @override_settings(PAYMENT_NOTIFICATION_RESEND_WEBHOOK_SECRET='whsec_test_secret')
    def test_resend_delivery_webhook_reconciles_a_previously_unknown_outcome(self):
        self._ensure_active_box_registry()
        _payment_id, delivery_id = self._create_due_email()
        event_time = timezone.now().replace(microsecond=0)
        with schema_context(TENANT_SCHEMA):
            delivery = PaymentNotificationDelivery.objects.get(pk=delivery_id)
            delivery.status = PaymentNotificationDeliveryStatus.UNKNOWN
            delivery.reason_code = 'email_outcome_unknown'
            delivery.finished_at = event_time
            delivery.save(update_fields=['status', 'reason_code', 'finished_at', 'updated_at'])

        payload = json.dumps({
            'type': 'email.delivered',
            'created_at': event_time.isoformat(),
            'data': {
                'email_id': 'resend-email-recovered',
                'tags': {'octobox_box': TENANT_SCHEMA, 'octobox_delivery': str(delivery_id)},
            },
        }).encode('utf-8')
        result = process_resend_payment_notification_webhook(
            payload=payload,
            headers=_resend_headers(
                event_id='evt_resend_reconcile_unknown', event_time=event_time, payload=payload,
            ),
        )

        with schema_context(TENANT_SCHEMA):
            delivery = PaymentNotificationDelivery.objects.get(pk=delivery_id)
        self.assertEqual(result['reason'], 'processed')
        self.assertEqual(delivery.status, PaymentNotificationDeliveryStatus.DELIVERED)
        self.assertEqual(delivery.reason_code, '')
        self.assertEqual(delivery.provider_message_id, 'resend-email-recovered')

    @override_settings(PAYMENT_NOTIFICATION_RESEND_WEBHOOK_SECRET='whsec_test_secret')
    def test_informational_complaint_cannot_hide_a_delayed_delivery_receipt(self):
        self._ensure_active_box_registry()
        _payment_id, delivery_id = self._create_due_email()
        received_at = timezone.now().replace(microsecond=0)
        for index, (event_type, occurred_at) in enumerate((
            ('email.complained', received_at),
            ('email.delivered', received_at - timedelta(seconds=5)),
        )):
            payload = json.dumps({
                'type': event_type, 'created_at': occurred_at.isoformat(),
                'data': {'email_id': 'resend-order-complaint', 'tags': {
                    'octobox_box': TENANT_SCHEMA, 'octobox_delivery': str(delivery_id),
                }},
            }).encode()
            process_resend_payment_notification_webhook(
                payload=payload, headers=_resend_headers(
                    event_id=f'evt_complaint_order_{index}', event_time=received_at, payload=payload,
                ),
            )
        with schema_context(TENANT_SCHEMA):
            delivery = PaymentNotificationDelivery.objects.get(pk=delivery_id)
            self.assertEqual(delivery.status, PaymentNotificationDeliveryStatus.DELIVERED)
            self.assertEqual(delivery.provider_events.count(), 2)

    @override_settings(PAYMENT_NOTIFICATION_RESEND_WEBHOOK_SECRET='whsec_test_secret')
    def test_equal_timestamp_events_use_highest_priority_not_last_inserted_event(self):
        self._ensure_active_box_registry()
        _payment_id, delivery_id = self._create_due_email()
        received_at = timezone.now().replace(microsecond=0)
        for index, event_type in enumerate(('email.failed', 'email.sent', 'email.delivery_delayed')):
            payload = json.dumps({
                'type': event_type, 'created_at': received_at.isoformat(),
                'data': {'email_id': 'resend-order-tie', 'tags': {
                    'octobox_box': TENANT_SCHEMA, 'octobox_delivery': str(delivery_id),
                }},
            }).encode()
            process_resend_payment_notification_webhook(
                payload=payload, headers=_resend_headers(
                    event_id=f'evt_equal_time_{index}', event_time=received_at, payload=payload,
                ),
            )
        with schema_context(TENANT_SCHEMA):
            delivery = PaymentNotificationDelivery.objects.get(pk=delivery_id)
            self.assertEqual(delivery.status, PaymentNotificationDeliveryStatus.FAILED)
            self.assertEqual(delivery.reason_code, 'resend_email_failed')
            self.assertEqual(delivery.provider_events.count(), 3)

    @override_settings(
        STUDENT_EMAIL_PROVIDER='resend',
        STUDENT_EMAIL_FROM='billing@example.test',
        STUDENT_RESEND_API_KEY='test-key',
    )
    @patch('signup.email_sender.urlopen')
    def test_resend_sender_serializes_correlation_tags(self, urlopen_mock):
        from signup.email_sender import send_html_email

        urlopen_mock.return_value.__enter__.return_value.read.return_value = b'{"id":"resend-email-tagged"}'
        tags = [
            {'name': 'octobox_box', 'value': TENANT_SCHEMA},
            {'name': 'octobox_delivery', 'value': '42'},
        ]

        result = send_html_email(
            subject='Pagamento confirmado',
            text_body='Texto',
            html_body='<p>Texto</p>',
            to_email='learner@example.test',
            tags=tags,
        )

        request = urlopen_mock.call_args.args[0]
        self.assertEqual(json.loads(request.data)['tags'], tags)
        self.assertEqual(result.provider_message_id, 'resend-email-tagged')

    @patch('finance.notification_outbox.enqueue_payment_confirmation', side_effect=RuntimeError('outbox write failed'))
    def test_outbox_write_failure_rolls_back_payment_reconciliation(self, _enqueue_mock):
        with schema_context(TENANT_SCHEMA):
            student = StudentFactory(email='learner@example.test')
            payment = PaymentFactory(student=student, amount=Decimal('149.90'), status=PaymentStatus.PENDING)
            payment_id = payment.pk

            with self.assertRaisesRegex(RuntimeError, 'outbox write failed'):
                execute_reconcile_payment_use_case(ReconcilePaymentCommand(
                    payment_id=payment_id,
                    amount_cents=14990,
                    stripe_event_id='evt_outbox_failure',
                    version_locked=0,
                ))

            payment.refresh_from_db()
            self.assertEqual(payment.status, PaymentStatus.PENDING)
            self.assertEqual(payment.version, 0)
            self.assertFalse(PaymentNotificationDelivery.objects.filter(payment_id=payment_id).exists())

    @override_settings(
        STUDENT_EMAIL_PROVIDER='resend',
        STUDENT_EMAIL_FROM='billing@example.test',
        STUDENT_RESEND_API_KEY='test-key',
    )
    @patch('signup.email_sender.send_html_email')
    def test_dispatch_records_provider_acceptance_without_recipient_pii(self, send_email):
        send_email.return_value = StudentEmailDeliveryResult(
            provider='resend',
            recipient='learner@example.test',
            provider_message_id='provider-message-123',
        )
        _payment_id, delivery_id = self._create_due_email()

        with schema_context(TENANT_SCHEMA):
            totals = run_due_payment_notification_deliveries(limit=5)
            delivery = PaymentNotificationDelivery.objects.get(pk=delivery_id)

        self.assertEqual(totals['provider_accepted'], 1)
        self.assertEqual(delivery.status, PaymentNotificationDeliveryStatus.PROVIDER_ACCEPTED)
        self.assertEqual(delivery.provider, 'resend')
        self.assertEqual(delivery.provider_message_id, 'provider-message-123')
        self.assertIsNone(delivery.delivered_at)
        self.assertTrue(delivery.recipient_key.startswith('student:'))
        self.assertNotIn('@', delivery.recipient_key)
        send_email.assert_called_once()
        self.assertEqual(
            send_email.call_args.kwargs['tags'],
            [
                {'name': 'octobox_box', 'value': TENANT_SCHEMA},
                {'name': 'octobox_delivery', 'value': str(delivery_id)},
            ],
        )

    @override_settings(
        STUDENT_EMAIL_PROVIDER='smtp',
        STUDENT_EMAIL_FROM='',
        EMAIL_HOST='localhost',
    )
    def test_missing_configuration_retries_later_with_safe_reason_code(self):
        _payment_id, delivery_id = self._create_due_email()

        with schema_context(TENANT_SCHEMA):
            totals = run_due_payment_notification_deliveries(limit=5)
            delivery = PaymentNotificationDelivery.objects.get(pk=delivery_id)

        self.assertEqual(totals['retry_wait'], 1)
        self.assertEqual(delivery.status, PaymentNotificationDeliveryStatus.RETRY_WAIT)
        self.assertEqual(delivery.reason_code, 'email_configuration_missing')
        self.assertGreater(delivery.available_at, timezone.now())

    def test_expired_lease_becomes_unknown_and_is_not_resent(self):
        _payment_id, delivery_id = self._create_due_email()
        with schema_context(TENANT_SCHEMA):
            delivery = PaymentNotificationDelivery.objects.get(pk=delivery_id)
            delivery.status = PaymentNotificationDeliveryStatus.LEASED
            delivery.lease_token = '2a8b52b8-6ad0-4cb5-a42d-48acc21f34cf'
            delivery.lease_expires_at = timezone.now() - timedelta(seconds=1)
            delivery.save(update_fields=['status', 'lease_token', 'lease_expires_at', 'updated_at'])

            claims = claim_due_payment_notification_deliveries(limit=5)
            delivery.refresh_from_db()

        self.assertEqual(claims, [])
        self.assertEqual(delivery.status, PaymentNotificationDeliveryStatus.UNKNOWN)
        self.assertEqual(delivery.reason_code, 'lease_expired_delivery_unknown')

    def test_intervention_queue_is_safe_and_counts_all_outbox_states(self):
        _payment_id, delivery_id = self._create_due_email()
        with schema_context(TENANT_SCHEMA):
            delivery = PaymentNotificationDelivery.objects.get(pk=delivery_id)
            delivery.status = PaymentNotificationDeliveryStatus.UNKNOWN
            delivery.reason_code = 'provider timeout with private details'
            delivery.save(update_fields=['status', 'reason_code', 'updated_at'])

            snapshot = build_payment_notification_operations_snapshot()

        self.assertEqual(snapshot['status_counts']['unknown'], 1)
        self.assertEqual(snapshot['attention_count'], 1)
        item = snapshot['attention_items'][0]
        self.assertEqual(item['delivery_id'], delivery_id)
        self.assertEqual(item['reason_code'], 'unclassified_reason')
        self.assertNotIn('recipient_key', item)
        self.assertNotIn('@', repr(snapshot))
        self.assertEqual(snapshot['attention_by_channel'], {'email': 1})
        self.assertEqual(snapshot['duplicate_suppressed_attempts'], 0)

    def test_duplicate_enqueue_is_counted_and_queue_age_is_reported(self):
        with schema_context(TENANT_SCHEMA):
            student = StudentFactory(email='learner@example.test')
            payment = PaymentFactory(student=student, amount=Decimal('149.90'), status=PaymentStatus.PAID)
            with transaction.atomic():
                from finance.notification_outbox import enqueue_payment_confirmation

                enqueue_payment_confirmation(payment)
                enqueue_payment_confirmation(payment)
            email_delivery = PaymentNotificationDelivery.objects.get(
                logical_event_key=f'payment-confirmed:v1:{payment.pk}',
                channel='email',
            )
            snapshot = build_payment_notification_operations_snapshot()

        self.assertEqual(email_delivery.duplicate_suppressed_count, 1)
        self.assertEqual(snapshot['duplicate_suppressed_attempts'], 3)
        self.assertIsNotNone(snapshot['oldest_queued_at'])
        self.assertGreaterEqual(snapshot['oldest_queued_age_seconds'], 0)

    @override_settings(
        STUDENT_EMAIL_PROVIDER='resend',
        STUDENT_EMAIL_FROM='billing@example.test',
        STUDENT_RESEND_API_KEY='test-key',
    )
    @patch('signup.email_sender.send_html_email')
    def test_scanner_recovers_committed_intent_when_post_commit_wakeup_fails(self, send_email):
        send_email.return_value = StudentEmailDeliveryResult(
            provider='resend', recipient='learner@example.test', provider_message_id='provider-recovered-1',
        )
        with schema_context(TENANT_SCHEMA):
            student = StudentFactory(email='learner@example.test')
            payment = PaymentFactory(student=student, amount=Decimal('149.90'), status=PaymentStatus.PENDING)
            payment_id = payment.pk

            with self.captureOnCommitCallbacks(execute=True):
                with patch(
                    'shared_support.background_jobs.run_in_background',
                    side_effect=RuntimeError('worker wakeup failed'),
                ):
                    execute_reconcile_payment_use_case(ReconcilePaymentCommand(
                        payment_id=payment_id,
                        amount_cents=14990,
                        stripe_event_id='evt_post_commit_wakeup_failure',
                        version_locked=0,
                    ))

            delivery = PaymentNotificationDelivery.objects.get(
                logical_event_key=f'payment-confirmed:v1:{payment_id}',
                channel='email',
            )
            self.assertEqual(delivery.status, PaymentNotificationDeliveryStatus.PENDING)
            totals = run_due_payment_notification_deliveries(limit=5)
            delivery.refresh_from_db()

        self.assertEqual(totals['provider_accepted'], 1)
        self.assertEqual(delivery.status, PaymentNotificationDeliveryStatus.PROVIDER_ACCEPTED)
        send_email.assert_called_once()

    @override_settings(
        STUDENT_EMAIL_PROVIDER='resend',
        STUDENT_EMAIL_FROM='billing@example.test',
        STUDENT_RESEND_API_KEY='test-key',
    )
    @patch('signup.email_sender.send_html_email')
    def test_worker_with_stale_lease_token_cannot_finalize_or_send(self, send_email):
        _payment_id, delivery_id = self._create_due_email()
        with schema_context(TENANT_SCHEMA):
            _claimed_id, old_token = claim_due_payment_notification_deliveries(limit=1)[0]
            new_token = uuid4()
            PaymentNotificationDelivery.objects.filter(pk=delivery_id).update(lease_token=new_token)

            result = dispatch_claimed_payment_notification_delivery(
                delivery_id=delivery_id,
                lease_token=old_token,
            )
            delivery = PaymentNotificationDelivery.objects.get(pk=delivery_id)

        self.assertEqual(result, 'lease_lost')
        self.assertEqual(delivery.status, PaymentNotificationDeliveryStatus.LEASED)
        self.assertEqual(delivery.lease_token, new_token)
        send_email.assert_not_called()

    @override_settings(
        STUDENT_EMAIL_PROVIDER='resend',
        STUDENT_EMAIL_FROM='billing@example.test',
        STUDENT_RESEND_API_KEY='test-key',
    )
    @patch('signup.email_sender.send_html_email', side_effect=TimeoutError('provider timeout'))
    def test_ambiguous_provider_failure_becomes_unknown_and_is_not_retried(self, send_email):
        _payment_id, delivery_id = self._create_due_email()
        with schema_context(TENANT_SCHEMA):
            delivery_id, token = claim_due_payment_notification_deliveries(limit=1)[0]
            result = dispatch_claimed_payment_notification_delivery(
                delivery_id=delivery_id,
                lease_token=token,
            )
            delivery = PaymentNotificationDelivery.objects.get(pk=delivery_id)
            next_claims = claim_due_payment_notification_deliveries(limit=5)

        self.assertEqual(result, PaymentNotificationDeliveryStatus.UNKNOWN)
        self.assertEqual(delivery.reason_code, 'email_outcome_unknown')
        self.assertEqual(next_claims, [])
        send_email.assert_called_once()


@pytest.mark.django_db(transaction=True)
@pytest.mark.requires_postgres
def test_two_workers_cannot_claim_the_same_delivery(test_tenant):
    with schema_context(test_tenant.schema_name):
        phone_suffix = uuid4().int % 10**10
        student = StudentFactory(email='parallel@example.test', phone=f'55119{phone_suffix:010d}')
        payment = PaymentFactory(student=student, status=PaymentStatus.PAID)
        delivery = PaymentNotificationDelivery.objects.create(
            payment=payment,
            logical_event_key=f'payment-confirmed:v1:{payment.pk}',
            channel='email',
            recipient_key=f'student:{student.pk}',
        )
        delivery_id = delivery.pk

    barrier = Barrier(2)

    def _claim_from_independent_connection():
        close_old_connections()
        try:
            barrier.wait(timeout=5)
            with schema_context(test_tenant.schema_name):
                return claim_due_payment_notification_deliveries(limit=1)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _index: _claim_from_independent_connection(), range(2)))

    matching_claims = [
        (claimed_id, token)
        for result in results
        for claimed_id, token in result
        if claimed_id == delivery_id
    ]
    assert len(matching_claims) == 1
    assert sum(len(result) for result in results) == 1
