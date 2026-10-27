import json

import pytest
from django.contrib import admin
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import RequestFactory, override_settings
from django_tenants.utils import get_public_schema_name, schema_context

from shared_support.crypto_codec import decode
from shared_support.crypto_fields import (
    generate_email_blind_index,
    generate_pending_signup_email_blind_index,
)
from signup.admin import PendingSignupAdmin
from signup.email_lookup import pending_signups_for_email
from signup.models import PendingSignup


pytestmark = pytest.mark.django_db


def _pending(email, **kwargs):
    return PendingSignup.objects.create(
        email=email,
        full_name=kwargs.pop('full_name', 'Aline Exemplo'),
        box_name=kwargs.pop('box_name', 'Box Exemplo'),
        **kwargs,
    )


def test_pending_signup_email_index_is_normalized_and_domain_separated():
    key = 'pending-signup-email-test-key'
    index = generate_pending_signup_email_blind_index(
        '  Athlete@Example.Test ', key=key,
    )
    assert index == generate_pending_signup_email_blind_index(
        'athlete@example.test', key=key,
    )
    assert index != generate_email_blind_index('athlete@example.test', key=key)


def test_pending_signup_dual_writes_index_with_update_fields():
    key = 'pending-signup-email-test-key'
    with schema_context(get_public_schema_name()), override_settings(EMAIL_BLIND_INDEX_KEY=key):
        pending = _pending('first@example.test')
        pending.email = 'Second@Example.Test'
        pending.save(update_fields=['email', 'updated_at'])
        pending.refresh_from_db()

    assert pending.email_lookup_index == generate_pending_signup_email_blind_index(
        pending.email, key=key,
    )


def test_pending_signup_save_keeps_email_and_index_aligned_across_partial_updates():
    key = 'pending-signup-email-test-key'
    old_email = 'before-partial@example.test'
    new_email = 'after-partial@example.test'
    with schema_context(get_public_schema_name()), override_settings(EMAIL_BLIND_INDEX_KEY=key):
        pending = _pending(old_email)
        old_index = generate_pending_signup_email_blind_index(old_email, key=key)
        pending.email = new_email
        pending.full_name = 'Updated Name'
        pending.save(update_fields=['full_name'])

        persisted = PendingSignup.objects.get(pk=pending.pk)
        assert persisted.email == old_email
        assert persisted.email_lookup_index == old_index

        pending.save(update_fields=['email'])
        pending.refresh_from_db()

    assert pending.email == new_email
    assert pending.email_lookup_index == generate_pending_signup_email_blind_index(
        new_email, key=key,
    )


def test_pending_signup_lookup_supports_legacy_and_hmac_and_revalidates_candidates():
    key = 'pending-signup-email-test-key'
    with schema_context(get_public_schema_name()), override_settings(EMAIL_BLIND_INDEX_KEY=key):
        target = _pending('Target@Example.Test')
        decoy = _pending('other@example.test')
        PendingSignup.objects.filter(pk=decoy.pk).update(
            email_lookup_index=generate_pending_signup_email_blind_index(
                target.email, key=key,
            ),
        )
        with override_settings(PENDING_SIGNUP_EMAIL_LOOKUP_INDEX_READY=False):
            legacy = pending_signups_for_email('target@example.test')
        with override_settings(PENDING_SIGNUP_EMAIL_LOOKUP_INDEX_READY=True):
            indexed = pending_signups_for_email(' target@example.test ')

    assert [row.pk for row in legacy] == [target.pk]
    assert [row.pk for row in indexed] == [target.pk]


def test_pending_signup_active_lookup_fails_closed_without_key():
    with override_settings(
        PENDING_SIGNUP_EMAIL_LOOKUP_INDEX_READY=True,
        EMAIL_BLIND_INDEX_KEY='',
    ):
        with pytest.raises(ImproperlyConfigured):
            pending_signups_for_email('person@example.test')


def test_pending_signup_rotation_requires_verified_lookup_gate():
    with override_settings(
        PENDING_SIGNUP_EMAIL_LOOKUP_INDEX_READY=False,
        EMAIL_BLIND_INDEX_KEY='',
    ), pytest.raises(CommandError, match='Ative e verifique o HMAC'):
        call_command(
            'rotate_pii_encryption',
            shared=True,
            model='PendingSignup',
            field='email',
        )


def test_pending_signup_admin_keeps_text_search_and_uses_exact_email():
    key = 'pending-signup-email-test-key'
    with schema_context(get_public_schema_name()), override_settings(
        EMAIL_BLIND_INDEX_KEY=key,
        PENDING_SIGNUP_EMAIL_LOOKUP_INDEX_READY=True,
    ):
        target = _pending('athlete@example.test', full_name='Aline Costa')
        other = _pending('athlete-two@example.test', full_name='Other Person')
        admin_view = PendingSignupAdmin(PendingSignup, admin.site)
        request = RequestFactory().get('/admin/signup/pendingsignup/')
        exact, _ = admin_view.get_search_results(
            request, PendingSignup.objects.all(), 'ATHLETE@example.test',
        )
        partial, _ = admin_view.get_search_results(
            request, PendingSignup.objects.all(), 'athlete@example',
        )
        by_name, _ = admin_view.get_search_results(
            request, PendingSignup.objects.all(), 'Aline Costa',
        )

    assert [row.pk for row in exact] == [target.pk]
    assert other.pk not in [row.pk for row in exact]
    assert not partial.exists()
    assert [row.pk for row in by_name] == [target.pk]


def test_pending_signup_email_writer_gate_preserves_plaintext_then_encrypts():
    key = 'pending-signup-email-test-key'
    with schema_context(get_public_schema_name()), override_settings(
        EMAIL_BLIND_INDEX_KEY=key,
        PENDING_SIGNUP_EMAIL_LOOKUP_INDEX_READY=True,
        PENDING_SIGNUP_EMAIL_ENCRYPTION_WRITE_READY=False,
    ):
        legacy = _pending('legacy-write@example.test')
        field = PendingSignup._meta.get_field('email')
        table = connection.ops.quote_name(PendingSignup._meta.db_table)
        column = connection.ops.quote_name(field.column)
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT {column} FROM {table} WHERE id = %s', [legacy.pk])
            legacy_raw = cursor.fetchone()[0]

    with schema_context(get_public_schema_name()), override_settings(
        EMAIL_BLIND_INDEX_KEY=key,
        PENDING_SIGNUP_EMAIL_LOOKUP_INDEX_READY=True,
        PENDING_SIGNUP_EMAIL_ENCRYPTION_WRITE_READY=True,
    ):
        encrypted = _pending('encrypted-write@example.test')
        table = connection.ops.quote_name(PendingSignup._meta.db_table)
        column = connection.ops.quote_name(field.column)
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT {column} FROM {table} WHERE id = %s', [encrypted.pk])
            encrypted_raw = cursor.fetchone()[0]
        encrypted.refresh_from_db()
        found = pending_signups_for_email('ENCRYPTED-WRITE@example.test')

    assert legacy_raw == 'legacy-write@example.test'
    assert field.max_length == 254
    assert field.db_type(connection) == 'varchar(2048)'
    assert field.db_index is False
    assert decode(encrypted_raw).plaintext == 'encrypted-write@example.test'
    assert encrypted.email == 'encrypted-write@example.test'
    assert [row.pk for row in found] == [encrypted.pk]


def test_pending_signup_email_backfill_is_cas_aggregate(capsys):
    schema = get_public_schema_name()
    key = 'pending-signup-email-test-key'
    with schema_context(schema), override_settings(EMAIL_BLIND_INDEX_KEY=key):
        pending = _pending('backfill@example.test')
        PendingSignup.objects.filter(pk=pending.pk).update(email_lookup_index='')
        with override_settings(
            PENDING_SIGNUP_EMAIL_LOOKUP_INDEX_READY=True,
            PENDING_SIGNUP_EMAIL_ENCRYPTION_WRITE_READY=True,
        ):
            encrypted_pending = _pending('encrypted-backfill@example.test')
            PendingSignup.objects.filter(pk=encrypted_pending.pk).update(email_lookup_index='')

    with override_settings(EMAIL_BLIND_INDEX_KEY=key):
        call_command('backfill_pending_signup_email_lookup_index')
        dry_run = json.loads(capsys.readouterr().out)
        call_command('backfill_pending_signup_email_lookup_index', apply=True, batch_size=1)
        applied = json.loads(capsys.readouterr().out)
        call_command('backfill_pending_signup_email_lookup_index', verify=True, batch_size=1)
        verified = json.loads(capsys.readouterr().out)

    with schema_context(schema):
        pending.refresh_from_db()
    assert dry_run['mode'] == 'dry-run'
    assert dry_run['written'] == 0
    assert dry_run['missing_index'] >= 1
    assert applied['written'] >= 2
    assert verified['verification_clean'] is True
    assert verified['complete_target_scan'] is True
    assert pending.email_lookup_index == generate_pending_signup_email_blind_index(
        pending.email, key=key,
    )
    assert encrypted_pending.email_lookup_index == generate_pending_signup_email_blind_index(
        encrypted_pending.email, key=key,
    )
    assert 'backfill@example.test' not in json.dumps([dry_run, applied, verified])
    assert 'encrypted-backfill@example.test' not in json.dumps([dry_run, applied, verified])
