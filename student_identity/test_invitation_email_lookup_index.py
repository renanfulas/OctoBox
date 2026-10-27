import json
from datetime import timedelta

import pytest
from django.contrib import admin
from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import RequestFactory, override_settings
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, schema_context

from shared_support.crypto_codec import decode
from shared_support.crypto_fields import (
    generate_email_blind_index,
    generate_student_app_invitation_email_blind_index,
)
from student_identity.admin import StudentAppInvitationAdmin
from student_identity.models import StudentAppInvitation
from student_identity.queries.invitation_email_lookup import invitations_for_email


pytestmark = pytest.mark.django_db


def _invitation(email):
    return StudentAppInvitation.objects.create(
        invited_email=email,
        expires_at=timezone.now() + timedelta(days=7),
    )


def test_invitation_email_index_normalizes_and_has_an_independent_domain():
    key = 'student-app-invitation-email-test-key'
    index = generate_student_app_invitation_email_blind_index(
        '  Athlete@Example.Test ', key=key,
    )
    assert index == generate_student_app_invitation_email_blind_index(
        'athlete@example.test', key=key,
    )
    assert index != generate_email_blind_index('athlete@example.test', key=key)


def test_encrypted_email_field_keeps_a_reader_first_writer_gate():
    key = 'student-app-invitation-email-test-key'
    with schema_context(get_public_schema_name()), override_settings(
        EMAIL_BLIND_INDEX_KEY=key,
        STUDENT_APP_INVITATION_EMAIL_LOOKUP_INDEX_READY=True,
        STUDENT_APP_INVITATION_EMAIL_ENCRYPTION_WRITE_READY=False,
    ):
        legacy_writer = _invitation('plaintext-until-readers@example.test')
        legacy_field = StudentAppInvitation._meta.get_field('invited_email')
        table = connection.ops.quote_name(StudentAppInvitation._meta.db_table)
        column = connection.ops.quote_name(legacy_field.column)
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT {column} FROM {table} WHERE id = %s', [legacy_writer.pk])
            stored_plaintext = cursor.fetchone()[0]
        legacy_writer.refresh_from_db()
        assert legacy_writer.invited_email == 'plaintext-until-readers@example.test'
        assert stored_plaintext == legacy_writer.invited_email

    with schema_context(get_public_schema_name()), override_settings(
        EMAIL_BLIND_INDEX_KEY=key,
        STUDENT_APP_INVITATION_EMAIL_LOOKUP_INDEX_READY=True,
        STUDENT_APP_INVITATION_EMAIL_ENCRYPTION_WRITE_READY=True,
    ):
        encrypted_writer = _invitation('encrypted-after-readers@example.test')
        field = StudentAppInvitation._meta.get_field('invited_email')
        table = connection.ops.quote_name(StudentAppInvitation._meta.db_table)
        column = connection.ops.quote_name(field.column)
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT {column} FROM {table} WHERE id = %s', [encrypted_writer.pk])
            stored_ciphertext = cursor.fetchone()[0]
        encrypted_writer.refresh_from_db()

    assert field.max_length == 254
    assert field.db_type(connection) == 'varchar(2048)'
    assert decode(stored_ciphertext).plaintext == 'encrypted-after-readers@example.test'
    assert encrypted_writer.invited_email == 'encrypted-after-readers@example.test'
    with pytest.raises(ValidationError):
        field.clean('not-an-email', encrypted_writer)


def test_invitation_save_dual_writes_email_index_with_update_fields():
    key = 'student-app-invitation-email-test-key'
    with schema_context(get_public_schema_name()), override_settings(EMAIL_BLIND_INDEX_KEY=key):
        invitation = _invitation('first@example.test')
        invitation.invited_email = 'Second@Example.Test'
        invitation.save(update_fields=['invited_email', 'updated_at'])
        invitation.refresh_from_db()

    assert invitation.email_lookup_index == generate_student_app_invitation_email_blind_index(
        invitation.invited_email, key=key,
    )


def test_invitation_save_keeps_email_and_index_aligned_across_partial_updates():
    key = 'student-app-invitation-email-test-key'
    old_email = 'before-partial@example.test'
    new_email = 'after-partial@example.test'
    with schema_context(get_public_schema_name()), override_settings(EMAIL_BLIND_INDEX_KEY=key):
        invitation = _invitation(old_email)
        old_index = generate_student_app_invitation_email_blind_index(old_email, key=key)
        invitation.invited_email = new_email
        invitation.student_name = 'Updated display name'
        invitation.save(update_fields=['student_name'])

        persisted = StudentAppInvitation.objects.get(pk=invitation.pk)
        assert persisted.invited_email == old_email
        assert persisted.email_lookup_index == old_index

        invitation.save(update_fields=['invited_email'])
        invitation.refresh_from_db()

    assert invitation.invited_email == new_email
    assert invitation.email_lookup_index == generate_student_app_invitation_email_blind_index(
        new_email, key=key,
    )


def test_invitation_lookup_legacy_and_indexed_modes_revalidate_email():
    key = 'student-app-invitation-email-test-key'
    with schema_context(get_public_schema_name()), override_settings(EMAIL_BLIND_INDEX_KEY=key):
        target = _invitation('Target@Example.Test')
        decoy = _invitation('other@example.test')
        StudentAppInvitation.objects.filter(pk=decoy.pk).update(
            email_lookup_index=generate_student_app_invitation_email_blind_index(
                target.invited_email, key=key,
            ),
        )
        with override_settings(STUDENT_APP_INVITATION_EMAIL_LOOKUP_INDEX_READY=False):
            legacy = invitations_for_email('target@example.test')
        with override_settings(STUDENT_APP_INVITATION_EMAIL_LOOKUP_INDEX_READY=True):
            indexed = invitations_for_email(' target@example.test ')

    assert [row.pk for row in legacy] == [target.pk]
    assert [row.pk for row in indexed] == [target.pk]


def test_indexed_lookup_reads_email_written_as_ciphertext():
    key = 'student-app-invitation-email-test-key'
    with schema_context(get_public_schema_name()), override_settings(
        EMAIL_BLIND_INDEX_KEY=key,
        STUDENT_APP_INVITATION_EMAIL_LOOKUP_INDEX_READY=True,
        STUDENT_APP_INVITATION_EMAIL_ENCRYPTION_WRITE_READY=True,
    ):
        target = _invitation('ciphertext-lookup@example.test')
        found = invitations_for_email('CIPHERTEXT-LOOKUP@example.test')
        table = connection.ops.quote_name(StudentAppInvitation._meta.db_table)
        column = connection.ops.quote_name(
            StudentAppInvitation._meta.get_field('invited_email').column,
        )
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT {column} FROM {table} WHERE id = %s', [target.pk])
            stored = cursor.fetchone()[0]

    assert decode(stored).status == 'legacy_fernet'
    assert [row.pk for row in found] == [target.pk]
    assert found[0].invited_email == 'ciphertext-lookup@example.test'


def test_invitation_admin_search_uses_exact_email_and_keeps_operational_search():
    key = 'student-app-invitation-email-test-key'
    with schema_context(get_public_schema_name()), override_settings(
        EMAIL_BLIND_INDEX_KEY=key,
        STUDENT_APP_INVITATION_EMAIL_LOOKUP_INDEX_READY=True,
    ):
        target = _invitation('athlete@example.test')
        partial = _invitation('athlete-two@example.test')
        admin_view = StudentAppInvitationAdmin(StudentAppInvitation, admin.site)
        request = RequestFactory().get('/admin/student_identity/studentappinvitation/')
        exact, _ = admin_view.get_search_results(
            request, StudentAppInvitation.objects.all(), 'athlete@example.test',
        )
        StudentAppInvitation.objects.filter(pk=target.pk).update(student_name='Athlete QA Name')
        by_name, _ = admin_view.get_search_results(
            request,
            StudentAppInvitation.objects.all(),
            'Athlete QA Name',
        )

    assert [row.pk for row in exact] == [target.pk]
    assert [row.pk for row in by_name] == [target.pk]
    assert partial.pk not in [row.pk for row in exact]


def test_invitation_email_index_backfill_dry_run_apply_verify_is_aggregate(capsys):
    schema = get_public_schema_name()
    key = 'student-app-invitation-email-test-key'
    with schema_context(schema), override_settings(EMAIL_BLIND_INDEX_KEY=key):
        invitation = _invitation('backfill@example.test')
        StudentAppInvitation.objects.filter(pk=invitation.pk).update(email_lookup_index='')

    with override_settings(EMAIL_BLIND_INDEX_KEY=key):
        call_command('backfill_student_app_invitation_email_lookup_index')
        dry_run = json.loads(capsys.readouterr().out)
        assert dry_run['mode'] == 'dry-run'
        assert dry_run['written'] == 0
        assert dry_run['missing_index'] >= 1
        call_command('backfill_student_app_invitation_email_lookup_index', apply=True)
        applied = json.loads(capsys.readouterr().out)
        call_command('backfill_student_app_invitation_email_lookup_index', verify=True)
        verified = json.loads(capsys.readouterr().out)

    with schema_context(schema):
        invitation.refresh_from_db()
    assert applied['written'] >= 1
    assert verified['verification_clean'] is True
    assert verified['drift'] == 0
    assert invitation.email_lookup_index == generate_student_app_invitation_email_blind_index(
        invitation.invited_email, key=key,
    )
    assert 'backfill@example.test' not in json.dumps([dry_run, applied, verified])
