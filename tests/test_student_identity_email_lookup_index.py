import json

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from shared_support.crypto_fields import generate_email_blind_index, generate_cpf_blind_index
from student_identity.models import StudentIdentity, StudentIdentityProvider, StudentIdentityStatus
from student_identity.queries.email_lookup import identities_for_email


class TestEmailBlindIndexUnitTests:
    def test_index_normalizes_case_and_whitespace_and_uses_its_own_domain(self):
        key = "email-index-test-key"
        first = generate_email_blind_index("  Member@Example.test ", key=key)
        second = generate_email_blind_index("member@example.test", key=key)

        assert first == second
        assert first.startswith("v1:")
        assert first != generate_cpf_blind_index("12345678900", key=key)
        assert generate_email_blind_index("", key=key) == ""
        assert generate_email_blind_index("member@example.test", key="") == ""


@pytest.mark.django_db(transaction=True)
def test_student_identity_email_index_dual_writes_only_when_key_is_configured():
    identity = StudentIdentity.objects.create(
        provider=StudentIdentityProvider.GOOGLE,
        provider_subject="email-index-dual-write",
        email="First@Example.test",
        status=StudentIdentityStatus.ACTIVE,
    )
    assert identity.email_lookup_index == ""

    with override_settings(EMAIL_BLIND_INDEX_KEY="email-index-test-key"):
        identity.email = "second@example.test"
        identity.save(update_fields={"email"})
        identity.refresh_from_db()
        assert identity.email_lookup_index == generate_email_blind_index(identity.email)

        current_index = identity.email_lookup_index
        identity.photo_url = "https://example.test/avatar.png"
        identity.save(update_fields={"photo_url"})
        identity.refresh_from_db()
        assert identity.email_lookup_index == current_index


@pytest.mark.django_db(transaction=True)
def test_email_lookup_keeps_legacy_path_until_ready_then_verifies_index_candidates():
    identity = StudentIdentity.objects.create(
        provider=StudentIdentityProvider.GOOGLE,
        provider_subject="email-index-lookup",
        email="Member@Example.test",
        status=StudentIdentityStatus.ACTIVE,
    )
    with override_settings(EMAIL_BLIND_INDEX_KEY="email-index-test-key"):
        identity.email_lookup_index = generate_email_blind_index(identity.email)
        identity.save(update_fields={"email_lookup_index"})
        assert [row.pk for row in identities_for_email(" MEMBER@example.test ")] == [identity.pk]

        with override_settings(STUDENT_IDENTITY_EMAIL_LOOKUP_INDEX_READY=False):
            assert [row.pk for row in identities_for_email(" MEMBER@example.test ")] == [identity.pk]

        with override_settings(STUDENT_IDENTITY_EMAIL_LOOKUP_INDEX_READY=True):
            # A different e-mail with the same stored HMAC must not be accepted.
            wrong = StudentIdentity.objects.create(
                provider=StudentIdentityProvider.GOOGLE,
                provider_subject="email-index-collision-guard",
                email="other@example.test",
                status=StudentIdentityStatus.ACTIVE,
            )
            StudentIdentity.objects.filter(pk=wrong.pk).update(email_lookup_index=identity.email_lookup_index)
            assert [row.pk for row in identities_for_email(" member@example.test ")] == [identity.pk]

    with override_settings(STUDENT_IDENTITY_EMAIL_LOOKUP_INDEX_READY=True, EMAIL_BLIND_INDEX_KEY=""):
        with pytest.raises(ImproperlyConfigured, match="EMAIL_BLIND_INDEX_KEY"):
            identities_for_email("member@example.test")


@pytest.mark.django_db(transaction=True)
def test_student_identity_form_conflict_check_uses_box_scope_and_exclusion():
    from student_app.forms import _student_identity_email_exists

    with override_settings(
        EMAIL_BLIND_INDEX_KEY="email-index-test-key",
        STUDENT_IDENTITY_EMAIL_LOOKUP_INDEX_READY=True,
    ):
        identity = StudentIdentity.objects.create(
            provider=StudentIdentityProvider.GOOGLE,
            provider_subject="email-index-form-lookup",
            email="form@example.test",
            box_root_slug="box-email-form",
            status=StudentIdentityStatus.ACTIVE,
        )
        assert _student_identity_email_exists(email="FORM@example.test", box_root_slug="box-email-form")
        assert not _student_identity_email_exists(
            email="form@example.test",
            box_root_slug="box-email-form",
            exclude_identity_id=identity.pk,
        )


@pytest.mark.django_db(transaction=True)
def test_email_index_backfill_apply_and_verify_are_aggregate_only(capsys):
    identity = StudentIdentity.objects.create(
        provider=StudentIdentityProvider.APPLE,
        provider_subject="email-index-backfill",
        email="backfill@example.test",
        status=StudentIdentityStatus.PENDING,
    )
    with override_settings(EMAIL_BLIND_INDEX_KEY="email-index-test-key"):
        missing_before = StudentIdentity.objects.filter(email_lookup_index="").exclude(email="").count()
        call_command("backfill_student_identity_email_lookup_index", apply=True, batch_size=1)
        report = json.loads(capsys.readouterr().out)
        assert report["mode"] == "apply"
        assert report["written"] == missing_before
        assert "backfill@example.test" not in json.dumps(report)

        identity.refresh_from_db()
        assert identity.email_lookup_index == generate_email_blind_index(identity.email)

        # The disposable database may contain rows left by shared test fixtures;
        # place the whole synthetic corpus on this test key before asserting a
        # clean complete-scan verification.
        for row in StudentIdentity.objects.only("pk", "email").iterator():
            StudentIdentity.objects.filter(pk=row.pk).update(
                email_lookup_index=generate_email_blind_index(row.email)
            )

        call_command("backfill_student_identity_email_lookup_index", verify=True, batch_size=1)
        report = json.loads(capsys.readouterr().out)
        assert report["mode"] == "verify"
        assert report["missing_index"] == 0
        assert report["drift"] == 0
        assert report["complete_target_scan"] is True
        assert report["duplicate_scan_complete"] is True


@pytest.mark.django_db(transaction=True)
def test_email_index_backfill_refuses_missing_key_without_writing(capsys):
    identity = StudentIdentity.objects.create(
        provider=StudentIdentityProvider.GOOGLE,
        provider_subject="email-index-no-key",
        email="no-key@example.test",
        status=StudentIdentityStatus.ACTIVE,
    )
    with override_settings(EMAIL_BLIND_INDEX_KEY=""):
        with pytest.raises(CommandError, match="EMAIL_BLIND_INDEX_KEY ausente"):
            call_command("backfill_student_identity_email_lookup_index", apply=True)
    identity.refresh_from_db()
    assert identity.email_lookup_index == ""


@pytest.mark.django_db(transaction=True)
def test_email_index_verify_reports_live_duplicates_without_exposing_addresses(capsys):
    with override_settings(EMAIL_BLIND_INDEX_KEY="email-index-test-key"):
        StudentIdentity.objects.create(
            provider=StudentIdentityProvider.GOOGLE,
            provider_subject="email-index-duplicate-a",
            email="Duplicate@Example.test",
            box_root_slug="box-email-duplicates",
            status=StudentIdentityStatus.ACTIVE,
        )
        StudentIdentity.objects.create(
            provider=StudentIdentityProvider.APPLE,
            provider_subject="email-index-duplicate-b",
            email="duplicate@example.test",
            box_root_slug="box-email-duplicates",
            status=StudentIdentityStatus.PENDING,
        )

        for row in StudentIdentity.objects.only("pk", "email").iterator():
            StudentIdentity.objects.filter(pk=row.pk).update(
                email_lookup_index=generate_email_blind_index(row.email)
            )

        call_command("backfill_student_identity_email_lookup_index", verify=True, batch_size=1)
        report = json.loads(capsys.readouterr().out)

    assert report["duplicate_scan_complete"] is True
    assert report["live_duplicate_index_groups_by_box_root"] >= 1
    assert "duplicate@example.test" not in json.dumps(report)
