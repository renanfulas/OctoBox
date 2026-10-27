import json
from datetime import timedelta

import pytest
from cryptography.fernet import Fernet
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, schema_context

from shared_support.crypto_codec import decode
from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutCheckoutLead,
    PublicWorkoutTier,
    PublicWorkoutWaitlistEntry,
)
from signup.models import PendingSignup
from student_identity.admin import StudentInvitationDeliveryAdmin
from student_identity.models import (
    StudentAppInvitation,
    StudentIdentity,
    StudentInvitationDelivery,
    StudentInvitationDeliveryStatus,
)


class SharedPIIAdminContractTests(SimpleTestCase):
    def test_delivery_admin_does_not_search_encrypted_recipient(self):
        model_admin = StudentInvitationDeliveryAdmin(StudentInvitationDelivery, admin.site)
        self.assertNotIn("recipient", model_admin.search_fields)


@pytest.mark.django_db(transaction=True)
def test_shared_census_and_rotation_cover_delivery_recipient(capsys, tmp_path):
    recipient = "shared-pii-census@example.test"
    public_schema = get_public_schema_name()
    with schema_context(public_schema):
        invitation = StudentAppInvitation.objects.create(
            student_name="Shared census canary",
            invited_email=recipient,
            expires_at=timezone.now() + timedelta(days=5),
        )
        delivery = StudentInvitationDelivery.objects.create(
            invitation=invitation,
            channel="email",
            provider="resend",
            status=StudentInvitationDeliveryStatus.SENT,
            recipient=recipient,
        )
        identity_email = "shared-identity-census@example.test"
        StudentIdentity.objects.create(
            provider="google",
            provider_subject="shared-census-google-subject",
            email=identity_email,
        )
        StudentAppInvitation.objects.create(
            student_name="Shared invite canary",
            invited_email="shared-invite-census@example.test",
            expires_at=timezone.now() + timedelta(days=5),
        )
        PublicWorkoutAccount.objects.create(email="shared-account-census@example.test")
        PublicWorkoutCheckoutLead.objects.create(
            email="shared-checkout-census@example.test",
            tier=PublicWorkoutTier.ESSENCIAL,
        )
        PublicWorkoutWaitlistEntry.objects.create(
            email="shared-waitlist-census@example.test",
            tier=PublicWorkoutTier.ESSENCIAL,
        )
        pending_signup = PendingSignup.objects.create(
            email="shared-signup-census@example.test",
            full_name="Shared census canary",
            box_name="Census Box",
        )
        get_user_model().objects.create_user(
            username="shared-census-user",
            email="shared-user-census@example.test",
        )
        field = StudentInvitationDelivery._meta.get_field("recipient")
        assert field.db_type(connection) == "varchar(2048)"
        invite_email_field = StudentAppInvitation._meta.get_field("invited_email")
        assert invite_email_field.db_type(connection) == "varchar(2048)"
        table = connection.ops.quote_name(StudentInvitationDelivery._meta.db_table)
        column = connection.ops.quote_name(field.column)
        with connection.cursor() as cursor:
            # Model writers encrypt. Install a plaintext canary to cover the
            # reader-first/backfill path without reading or changing live data.
            cursor.execute(
                f"UPDATE {table} SET {column} = %s WHERE id = %s",
                [recipient, delivery.pk],
            )
            cursor.execute(f"SELECT {column} FROM {table} WHERE id = %s", [delivery.pk])
            original_value = cursor.fetchone()[0]
        assert original_value == recipient

    call_command("report_pii_encryption_formats", shared=True, batch_size=2)
    census = json.loads(capsys.readouterr().out)
    assert census["scope"] == "shared"
    assert census["schema"] == public_schema
    census_fields = {(row["model"], row["field"]): row for row in census["fields"]}
    assert set(census_fields) == {
        ("StudentInvitationDelivery", "recipient"),
        ("StudentIdentity", "email"),
        ("StudentAppInvitation", "invited_email"),
        ("PublicWorkoutAccount", "email"),
        ("PublicWorkoutCheckoutLead", "email"),
        ("PublicWorkoutWaitlistEntry", "email"),
        ("PendingSignup", "email"),
        ("User", "email"),
    }
    assert census_fields[("StudentInvitationDelivery", "recipient")] == {
        "model": "StudentInvitationDelivery",
        "field": "recipient",
        "stored_plaintext": False,
        "rows": 1,
        "format_counts": {"legacy_plaintext": 1},
        "max_stored_characters": len(recipient),
        "max_readable_plaintext_characters": len(recipient),
        "readable_over_logical_limit": 0,
    }
    invite_email_census = census_fields[("StudentAppInvitation", "invited_email")]
    assert invite_email_census["stored_plaintext"] is False
    assert invite_email_census["rows"] == 2
    assert invite_email_census["format_counts"] == {"legacy_plaintext": 2}
    pending_signup_census = census_fields[("PendingSignup", "email")]
    assert pending_signup_census["stored_plaintext"] is False
    assert pending_signup_census["rows"] == 1
    assert pending_signup_census["format_counts"] == {"legacy_plaintext": 1}
    for key in set(census_fields) - {
        ("StudentInvitationDelivery", "recipient"),
        ("StudentAppInvitation", "invited_email"),
        ("PendingSignup", "email"),
    }:
        assert census_fields[key]["stored_plaintext"] is True
        assert "unencrypted_plaintext" in census_fields[key]["format_counts"]
    for secret in (
        recipient,
        identity_email,
        "shared-invite-census@example.test",
        "shared-account-census@example.test",
        "shared-checkout-census@example.test",
        "shared-waitlist-census@example.test",
        "shared-signup-census@example.test",
        "shared-user-census@example.test",
    ):
        assert secret not in json.dumps(census)

    key_id = "shared-recipient-test"
    key = Fernet.generate_key().decode("ascii")
    with override_settings(
        PII_ENCRYPTION_KEYRING_JSON=json.dumps({key_id: key}),
        PII_ENCRYPTION_ACTIVE_KEY_ID=key_id,
    ):
        call_command(
            "rotate_pii_encryption",
            shared=True,
            model="StudentInvitationDelivery",
            field="recipient",
            apply=True,
            checkpoint=str(tmp_path / "shared-recipient-checkpoint.json"),
        )
        report = json.loads(capsys.readouterr().out)
        assert report["scope"] == "shared"
        assert report["schema"] == public_schema
        assert report["written"] == 1
        assert recipient not in json.dumps(report)

        call_command(
            "rotate_pii_encryption",
            shared=True,
            model="StudentAppInvitation",
            field="invited_email",
            apply=True,
            checkpoint=str(tmp_path / "shared-invitation-checkpoint.json"),
        )
        invitation_report = json.loads(capsys.readouterr().out)
        assert invitation_report["scope"] == "shared"
        assert invitation_report["written"] == 2
        assert "shared-pii-census@example.test" not in json.dumps(invitation_report)

        with override_settings(
            PENDING_SIGNUP_EMAIL_LOOKUP_INDEX_READY=True,
            EMAIL_BLIND_INDEX_KEY="shared-pending-signup-index-test-key",
        ):
            call_command(
                "rotate_pii_encryption",
                shared=True,
                model="PendingSignup",
                field="email",
                apply=True,
                checkpoint=str(tmp_path / "shared-pending-signup-checkpoint.json"),
            )
            pending_signup_report = json.loads(capsys.readouterr().out)
            assert pending_signup_report["written"] == 1
            assert "shared-signup-census@example.test" not in json.dumps(pending_signup_report)

        with schema_context(public_schema):
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT {column} FROM {table} WHERE id = %s", [delivery.pk])
                rotated_value = cursor.fetchone()[0]
            decoded = decode(rotated_value)
            assert decoded.status == "envelope"
            assert decoded.key_id == key_id
            assert decoded.plaintext == recipient
            delivery.refresh_from_db()
            assert delivery.recipient == recipient
            invite_table = connection.ops.quote_name(StudentAppInvitation._meta.db_table)
            invite_column = connection.ops.quote_name(
                StudentAppInvitation._meta.get_field("invited_email").column,
            )
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT {invite_column} FROM {invite_table} WHERE id = %s",
                    [invitation.pk],
                )
                invite_rotated_value = cursor.fetchone()[0]
            invite_decoded = decode(invite_rotated_value)
            assert invite_decoded.status == "envelope"
            assert invite_decoded.key_id == key_id
            assert invite_decoded.plaintext == recipient
            invitation.refresh_from_db()
            assert invitation.invited_email == recipient
            pending_signup.refresh_from_db()
            assert pending_signup.email == "shared-signup-census@example.test"

    checkpoint = (tmp_path / "shared-recipient-checkpoint.json").read_text(encoding="utf-8")
    assert recipient not in checkpoint
    invitation_checkpoint = (tmp_path / "shared-invitation-checkpoint.json").read_text(encoding="utf-8")
    assert recipient not in invitation_checkpoint
