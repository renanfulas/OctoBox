from __future__ import annotations

import json
from io import StringIO
import threading
import uuid
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connections
from django.test import RequestFactory, TransactionTestCase
from django.utils import timezone
from django_tenants.utils import schema_context
import pytest

from communications.models import WhatsAppContact, WhatsAppMessageLog
from control.models import Box, Domain, Membership
from control.tenant_write_fence import (
    TenantWritesFrozen,
    set_tenant_write_fence,
    tenant_write_guard,
    tenant_write_exclusive,
)
from control.write_fence_middleware import TenantWriteFenceMiddleware
from integrations.stripe.models import PaymentWebhookEvent, PaymentWebhookStatus
from integrations.stripe.router import route_payment_webhook_event
from jobs.models import AsyncJob
from student_identity.models import (
    StudentAppInvitation,
    StudentBoxInviteLink,
    StudentInvitationDelivery,
    StudentInvitationDeliveryEvent,
    StudentInvitationDeliveryStatus,
)
from student_identity.resend_webhooks import ResendWebhookHeaders, process_resend_webhook
from student_app.models import MovementLibrary
from students.models import Student


@pytest.mark.public_schema
class TenantWriteFenceTest(TransactionTestCase):
    def _fixture_teardown(self):
        # TransactionTestCase's global flush removes the session-scoped
        # box_test fixture, while tenant schemas can retain cross-schema FKs.
        # Clean only rows this class owns and preserve the shared test tenant.
        for db_connection in connections.all():
            if hasattr(db_connection, 'set_schema_to_public'):
                db_connection.set_schema_to_public()
        if getattr(self, 'b_canary_student_id', None):
            with schema_context('box_test'):
                Student.objects.filter(pk=self.b_canary_student_id).delete()
        with schema_context('box_test'):
            WhatsAppMessageLog.objects.filter(
                contact_id__in=getattr(self, 'whatsapp_test_contact_ids', []),
            ).delete()
            WhatsAppContact.objects.filter(
                pk__in=getattr(self, 'whatsapp_test_contact_ids', []),
            ).delete()
        if getattr(self, 'fence_delete_user_id', None):
            get_user_model().objects.filter(pk=self.fence_delete_user_id).delete()
        box_ids = [self.box_a.pk, self.box_b.pk]
        StudentInvitationDeliveryEvent.objects.filter(
            delivery__invitation__box_id__in=box_ids,
        ).delete()
        StudentInvitationDelivery.objects.filter(invitation__box_id__in=box_ids).delete()
        StudentAppInvitation.objects.filter(box_id__in=box_ids).delete()
        StudentBoxInviteLink.objects.filter(box_id__in=box_ids).delete()
        PaymentWebhookEvent.objects.filter(event_id='evt-fence-alpha').delete()
        Membership.objects.filter(box_id__in=box_ids).delete()
        Domain.objects.filter(tenant_id__in=box_ids).delete()
        Box.objects.filter(pk__in=box_ids).delete()

    def setUp(self):
        self.whatsapp_test_contact_ids = []
        user = get_user_model().objects.get(username='__pytest_test_tenant_owner__')
        self.box_a = Box.objects.create(
            slug='fence-alpha', schema_name='box_fence_alpha', display_name='Fence Alpha',
            status=Box.Status.ACTIVE, owner_user=user,
        )
        self.box_b = Box.objects.create(
            slug='fence-bravo', schema_name='box_fence_bravo', display_name='Fence Bravo',
            status=Box.Status.ACTIVE, owner_user=user,
        )


    def test_freeze_is_idempotent_and_unfreeze_releases_box(self):
        frozen, changed = set_tenant_write_fence(
            schema_name=self.box_a.schema_name,
            frozen=True,
            reason='restore drill',
        )
        self.assertTrue(changed)
        first_frozen_at = frozen.write_frozen_at
        self.assertIsNotNone(first_frozen_at)
        self.assertEqual(frozen.write_freeze_reason, 'restore drill')

        frozen_again, changed_again = set_tenant_write_fence(
            schema_name=self.box_a.schema_name,
            frozen=True,
            reason='restore drill',
        )
        self.assertFalse(changed_again)
        self.assertEqual(frozen_again.write_frozen_at, first_frozen_at)

        with self.assertRaises(TenantWritesFrozen):
            with tenant_write_guard(self.box_a.schema_name):
                self.fail('box congelado nao deve entrar no trabalho')

        with tenant_write_guard(self.box_b.schema_name) as box:
            self.assertEqual(box.pk, self.box_b.pk)

        released, changed_release = set_tenant_write_fence(
            schema_name=self.box_a.schema_name,
            frozen=False,
        )
        self.assertTrue(changed_release)
        self.assertIsNone(released.write_frozen_at)
        self.assertEqual(released.write_freeze_reason, '')
        with tenant_write_guard(self.box_a.schema_name):
            pass

    def test_frozen_a_rejects_business_write_while_b_persists_student(self):
        box_b = Box.objects.get(schema_name='box_test')
        set_tenant_write_fence(
            schema_name=self.box_a.schema_name,
            frozen=True,
            reason='selective restore test',
        )

        with self.assertRaises(TenantWritesFrozen):
            with tenant_write_guard(self.box_a.schema_name):
                with schema_context(self.box_a.schema_name):
                    Student.objects.create(
                        full_name='Must Not Persist In A',
                        phone=f"55119{uuid.uuid4().int % 10**8:08d}",
                    )

        with tenant_write_guard(box_b.schema_name):
            with schema_context(box_b.schema_name):
                student = Student.objects.create(
                    full_name='Restore Canary B',
                    phone=f"55119{uuid.uuid4().int % 10**8:08d}",
                )
                self.b_canary_student_id = student.pk
                self.assertTrue(Student.objects.filter(pk=student.pk).exists())


    def test_http_middleware_returns_retryable_service_unavailable(self):
        set_tenant_write_fence(
            schema_name=self.box_a.schema_name,
            frozen=True,
            reason='restore drill',
        )
        called = []
        request = RequestFactory().post('/operacao/wod/')
        request.tenant = self.box_a
        response = TenantWriteFenceMiddleware(lambda _request: called.append(True))(request)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response['Retry-After'], '60')
        self.assertEqual(response['X-Octobox-Tenant-Frozen'], '1')
        self.assertEqual(called, [])

    def test_open_student_sse_does_not_block_tenant_freeze(self):
        from shared_support import student_event_stream

        stream_waiting_for_redis = threading.Event()
        stop_stream = threading.Event()
        stream_closed = threading.Event()
        freeze_finished = threading.Event()
        errors = []

        class StopTestStream(Exception):
            pass

        class FakePubSub:
            def subscribe(self, _channel):
                return None

            def get_message(self, timeout=None):
                stream_waiting_for_redis.set()
                if not stop_stream.wait(5):
                    raise TimeoutError('SSE test stream stop timed out')
                raise StopTestStream

            def close(self):
                stream_closed.set()

        pubsub = FakePubSub()
        fake_redis = SimpleNamespace(pubsub=lambda **_kwargs: pubsub)
        request = RequestFactory().get('/students/42/events/')
        request.tenant = self.box_a
        response = None
        consumer_thread = None
        freeze_thread = None
        consumer_still_running = False
        freezer_still_running = False

        def consume_stream():
            try:
                for _chunk in response.streaming_content:
                    pass
            except StopTestStream:
                pass
            except Exception as exc:  # bubble failures from the stream thread
                errors.append(exc)

        def freeze_box():
            connections.close_all()
            try:
                set_tenant_write_fence(
                    schema_name=self.box_a.schema_name,
                    frozen=True,
                    reason='SSE drain regression',
                )
                freeze_finished.set()
            except Exception as exc:  # bubble failures from the freezer thread
                errors.append(exc)
            finally:
                connections.close_all()

        try:
            with (
                patch.object(
                    student_event_stream,
                    'build_student_event_channel',
                    return_value='octobox:tenant:box_fence_alpha:student:42:events',
                ),
                patch.object(student_event_stream, 'get_redis_client', return_value=fake_redis),
                patch.object(student_event_stream, 'record_student_sse_stream_connection'),
                patch.object(student_event_stream, 'inc_student_sse_active_streams'),
                patch.object(student_event_stream, 'dec_student_sse_active_streams'),
                patch.object(student_event_stream, 'record_student_sse_event_published'),
            ):
                response = TenantWriteFenceMiddleware(
                    lambda _request: student_event_stream.build_student_event_stream(student_id=42)
                )(request)
                consumer_thread = threading.Thread(target=consume_stream, daemon=True)
                consumer_thread.start()
                self.assertTrue(stream_waiting_for_redis.wait(5), 'SSE stream did not reach Redis read')
                self.assertTrue(consumer_thread.is_alive(), 'SSE stream ended before freeze started')

                freeze_thread = threading.Thread(target=freeze_box, daemon=True)
                freeze_thread.start()
                self.assertTrue(
                    freeze_finished.wait(5),
                    'open read-only SSE stream kept the tenant shared fence lease',
                )
                self.assertTrue(consumer_thread.is_alive(), 'SSE stream was closed by the freeze')
        finally:
            stop_stream.set()
            if consumer_thread is not None:
                consumer_thread.join(5)
                consumer_still_running = consumer_thread.is_alive()
            if freeze_thread is not None:
                freeze_thread.join(5)
                freezer_still_running = freeze_thread.is_alive()
            connections.close_all()
            if freeze_thread is not None and freezer_still_running:
                freeze_thread.join(1)
                freezer_still_running = freeze_thread.is_alive()
            set_tenant_write_fence(schema_name=self.box_a.schema_name, frozen=False)

        self.assertTrue(freeze_finished.is_set(), 'tenant freeze did not finish while SSE remained open')
        self.assertFalse(consumer_still_running, 'SSE consumer did not close')
        self.assertFalse(freezer_still_running, 'tenant freeze thread did not finish')
        self.assertTrue(stream_closed.is_set(), 'SSE Pub/Sub connection was not closed')
        self.assertEqual(errors, [])
        self.box_a.refresh_from_db()
        self.assertIsNone(self.box_a.write_frozen_at)

    def test_tenant_sweep_skips_frozen_box_without_failing_the_batch(self):
        from shared_support.tenant_sweep import sweep_active_tenants

        set_tenant_write_fence(
            schema_name=self.box_a.schema_name,
            frozen=True,
            reason='restore drill',
        )
        visited = []
        sweep = sweep_active_tenants(
            lambda box: visited.append(box.schema_name),
            only_schema=self.box_a.schema_name,
        )

        self.assertEqual(visited, [])
        self.assertEqual(sweep.schemas_skipped, 1)
        self.assertEqual(sweep.schemas_failed, 0)

    def test_public_onboarding_audit_cannot_write_into_frozen_tenant(self):
        from student_identity.funnel_events import record_student_onboarding_event

        set_tenant_write_fence(
            schema_name=self.box_a.schema_name,
            frozen=True,
            reason='restore drill',
        )

        with self.assertRaises(TenantWritesFrozen):
            record_student_onboarding_event(
                journey='imported_lead_invite',
                event='invite_created',
                target_model='student_identity.StudentAppInvitation',
                target_id='frozen-invite-1',
                metadata={
                    'box_root_slug': self.box_a.schema_name,
                    'invitation_id': 'frozen-invite-1',
                },
            )

    def test_public_onboarding_audit_without_box_attribution_is_skipped(self):
        from student_identity.funnel_events import record_student_onboarding_event

        result = record_student_onboarding_event(
            journey='imported_lead_invite',
            event='invite_created',
            target_model='student_identity.StudentAppInvitation',
            target_id='unattributed-invite',
        )

        self.assertIsNone(result)

    def test_stripe_event_for_frozen_tenant_is_deferred_without_consuming_retries(self):
        set_tenant_write_fence(
            schema_name=self.box_a.schema_name,
            frozen=True,
            reason='restore drill',
        )
        event = PaymentWebhookEvent.objects.create(
            event_id='evt-fence-alpha',
            event_type='checkout.session.completed',
            payload={
                'data': {
                    'object': {
                        'metadata': {
                            'payment_id': '10',
                            'box_schema': self.box_a.schema_name,
                        },
                    },
                },
            },
        )

        route_payment_webhook_event(event)
        event.refresh_from_db()

        self.assertEqual(event.status, PaymentWebhookStatus.PENDING)
        self.assertEqual(event.attempts, 0)
        self.assertIsNotNone(event.next_retry_at)
        self.assertIn(self.box_a.schema_name, event.last_error_message)

    def test_resend_event_for_frozen_tenant_is_rejected_and_shared_update_rolls_back(self):
        set_tenant_write_fence(
            schema_name=self.box_a.schema_name,
            frozen=True,
            reason='restore drill',
        )
        invitation = StudentAppInvitation.objects.create(
            student_name='Canary Student',
            invited_email='canary@example.test',
            expires_at=timezone.now() + timedelta(days=2),
            box=self.box_a,
            box_root_slug=self.box_a.schema_name,
        )
        delivery = StudentInvitationDelivery.objects.create(
            invitation=invitation,
            channel='email',
            provider='resend',
            status=StudentInvitationDeliveryStatus.SENT,
            recipient='canary@example.test',
            provider_message_id='email-fence-alpha',
        )
        payload = json.dumps({
            'type': 'email.delivered',
            'data': {'email_id': delivery.provider_message_id},
        }).encode('utf-8')

        with patch('student_identity.resend_webhooks.verify_resend_webhook_signature'):
            with self.assertRaises(TenantWritesFrozen):
                process_resend_webhook(
                    payload=payload,
                    headers=ResendWebhookHeaders(
                        webhook_id='msg-fence-alpha',
                        timestamp='1',
                        signature='v1,test',
                    ),
                )

        delivery.refresh_from_db()
        self.assertEqual(delivery.status, StudentInvitationDeliveryStatus.SENT)
        self.assertFalse(
            StudentInvitationDeliveryEvent.objects.filter(provider_event_id='msg-fence-alpha').exists()
        )

    def test_freeze_transition_waits_for_inflight_tenant_work(self):
        acquired = threading.Event()
        release_writer = threading.Event()
        freeze_started = threading.Event()
        freeze_finished = threading.Event()
        errors = []

        def writer():
            connections.close_all()
            try:
                with tenant_write_guard(self.box_a.schema_name):
                    acquired.set()
                    if not release_writer.wait(5):
                        raise TimeoutError('writer test barrier timed out')
            except Exception as exc:  # bubble failures from thread to the test
                errors.append(exc)
            finally:
                connections.close_all()

        def freezer():
            connections.close_all()
            try:
                freeze_started.set()
                set_tenant_write_fence(
                    schema_name=self.box_a.schema_name,
                    frozen=True,
                    reason='concurrency test',
                )
                freeze_finished.set()
            except Exception as exc:
                errors.append(exc)
            finally:
                connections.close_all()

        writer_thread = threading.Thread(target=writer, daemon=True)
        freeze_thread = threading.Thread(target=freezer, daemon=True)
        writer_thread.start()
        self.assertTrue(acquired.wait(5), 'writer did not acquire the shared fence')
        freeze_thread.start()
        try:
            self.assertTrue(freeze_started.wait(5))
            self.assertFalse(freeze_finished.wait(0.2), 'freeze passed an active writer')
        finally:
            release_writer.set()

        writer_thread.join(5)
        freeze_thread.join(5)
        self.assertFalse(writer_thread.is_alive())
        self.assertFalse(freeze_thread.is_alive())
        self.assertEqual(errors, [])
        self.box_a.refresh_from_db()
        self.assertLessEqual(self.box_a.write_frozen_at, timezone.now())

    def test_exclusive_lifecycle_lock_waits_for_inflight_tenant_work(self):
        acquired = threading.Event()
        release_writer = threading.Event()
        exclusive_started = threading.Event()
        exclusive_finished = threading.Event()
        errors = []

        def writer():
            connections.close_all()
            try:
                with tenant_write_guard(self.box_a.schema_name):
                    acquired.set()
                    if not release_writer.wait(5):
                        raise TimeoutError('writer test barrier timed out')
            except Exception as exc:  # bubble failures from thread to the test
                errors.append(exc)
            finally:
                connections.close_all()

        def lifecycle_operation():
            connections.close_all()
            try:
                exclusive_started.set()
                with tenant_write_exclusive(self.box_a.schema_name):
                    exclusive_finished.set()
            except Exception as exc:
                errors.append(exc)
            finally:
                connections.close_all()

        writer_thread = threading.Thread(target=writer, daemon=True)
        lifecycle_thread = threading.Thread(target=lifecycle_operation, daemon=True)
        writer_thread.start()
        self.assertTrue(acquired.wait(5), 'writer did not acquire the shared fence')
        lifecycle_thread.start()
        try:
            self.assertTrue(exclusive_started.wait(5))
            self.assertFalse(exclusive_finished.wait(0.2), 'lifecycle lock passed an active writer')
        finally:
            release_writer.set()

        writer_thread.join(5)
        lifecycle_thread.join(5)
        self.assertFalse(writer_thread.is_alive())
        self.assertFalse(lifecycle_thread.is_alive())
        self.assertTrue(exclusive_finished.is_set())
        self.assertEqual(errors, [])

    def test_exclusive_lifecycle_lock_refuses_a_frozen_box(self):
        set_tenant_write_fence(
            schema_name=self.box_a.schema_name,
            frozen=True,
            reason='restore in progress',
        )

        with self.assertRaises(TenantWritesFrozen):
            with tenant_write_exclusive(self.box_a.schema_name):
                self.fail('lifecycle operation must not bypass an active freeze')

    def test_safe_user_delete_aborts_before_shared_delete_if_any_box_is_frozen(self):
        from control.services import delete_user_safely

        user = get_user_model().objects.create_user(
            username=f'fence-delete-{uuid.uuid4().hex[:10]}',
            password='test-only-password',
        )
        self.fence_delete_user_id = user.pk
        Membership.objects.create(user=user, box=self.box_a, role='coach')
        Membership.objects.create(user=user, box=self.box_b, role='coach')
        set_tenant_write_fence(
            schema_name=self.box_b.schema_name,
            frozen=True,
            reason='restore in progress',
        )

        with patch('control.services._tenant_user_fk_fields', return_value=[]):
            with self.assertRaises(TenantWritesFrozen):
                delete_user_safely(user)

        self.assertTrue(get_user_model().objects.filter(pk=user.pk).exists())
        self.assertEqual(
            Membership.objects.filter(user=user, box__in=[self.box_a, self.box_b]).count(),
            2,
        )
        user.delete()





    def test_frozen_tenant_blocks_demo_seed_and_destructive_reset_commands(self):
        box = Box.objects.get(schema_name='box_test')
        set_tenant_write_fence(
            schema_name=box.schema_name,
            frozen=True,
            reason='restore in progress',
        )
        try:
            with schema_context(box.schema_name):
                for command, options in (
                    ('seed_south_sp_box', {}),
                    ('seed_pilot_workspace', {}),
                    ('reset_demo_workspace', {}),
                ):
                    with self.subTest(command=command):
                        with self.assertRaisesRegex(CommandError, 'está congelado'):
                            call_command(command, **options)
        finally:
            set_tenant_write_fence(schema_name=box.schema_name, frozen=False)

    def test_demo_seed_commands_refuse_public_schema(self):
        with self.assertRaisesRegex(CommandError, 'dentro de um schema de box'):
            call_command('seed_pilot_workspace')

    def test_frozen_test_tenant_blocks_performance_data_population(self):
        box = Box.objects.get(schema_name='box_test')
        with schema_context(box.schema_name):
            student_count = Student.objects.count()
        set_tenant_write_fence(
            schema_name=box.schema_name,
            frozen=True,
            reason='restore in progress',
        )
        try:
            with self.assertRaisesRegex(CommandError, 'está congelado'):
                call_command('populate_test_db', records=1)
            with schema_context(box.schema_name):
                self.assertEqual(Student.objects.count(), student_count)
        finally:
            set_tenant_write_fence(schema_name=box.schema_name, frozen=False)

    def test_populate_test_db_rejects_unexpected_box_schema_cleanly(self):
        from types import SimpleNamespace

        with patch('control.models.Box.objects.filter') as box_filter:
            box_filter.return_value.first.return_value = SimpleNamespace(schema_name='box_wrong')
            with self.assertRaisesRegex(CommandError, 'deve usar box_test'):
                call_command('populate_test_db', records=1)

    def test_frozen_box_blocks_cross_schema_onboarding_seed_before_shared_writes(self):
        box = self.box_a
        invitation_count = StudentAppInvitation.objects.filter(box=box).count()
        invite_link_count = StudentBoxInviteLink.objects.filter(box=box).count()
        set_tenant_write_fence(
            schema_name=box.schema_name,
            frozen=True,
            reason='restore in progress',
        )
        try:
            with self.assertRaisesRegex(CommandError, 'está congelado'):
                call_command('seed_onboarding_scenarios', box_slug=box.slug)
            self.assertEqual(StudentAppInvitation.objects.filter(box=box).count(), invitation_count)
            self.assertEqual(StudentBoxInviteLink.objects.filter(box=box).count(), invite_link_count)
        finally:
            set_tenant_write_fence(schema_name=box.schema_name, frozen=False)


    def test_frozen_box_blocks_legacy_tenant_maintenance_writers(self):
        box = Box.objects.get(schema_name='box_test')
        with schema_context(box.schema_name):
            student_count = Student.objects.count()
            movement_count = MovementLibrary.objects.count()
        membership_count = Membership.objects.filter(box=box).count()
        set_tenant_write_fence(
            schema_name=box.schema_name,
            frozen=True,
            reason='restore in progress',
        )
        try:
            commands = (
                ('import_students_csv', ('must-not-be-opened.csv',), {'schema': box.schema_name}),
                ('seed_dashboard', (), {'schema': box.schema_name}),
                ('seed_movement_library', (), {'schema': box.schema_name}),
                ('backfill_staff_membership', (), {'box': box.slug}),
            )
            for command, args, options in commands:
                with self.subTest(command=command):
                    with self.assertRaisesRegex(CommandError, 'está congelado'):
                        call_command(command, *args, **options)
            with schema_context(box.schema_name):
                self.assertEqual(Student.objects.count(), student_count)
                self.assertEqual(MovementLibrary.objects.count(), movement_count)
            self.assertEqual(Membership.objects.filter(box=box).count(), membership_count)
        finally:
            set_tenant_write_fence(schema_name=box.schema_name, frozen=False)
