import json

import pytest
from cryptography.fernet import Fernet
from django.core.management import call_command, CommandError
from django.db import connection
from django.test import override_settings

from shared_support.crypto_codec import decode
from shared_support.crypto_keyring import derive_legacy_fernet_key
from students.models import Student


pytestmark = pytest.mark.django_db(transaction=True)


def _raw_student_phone(student_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT phone FROM boxcore_student WHERE id = %s", [student_id])
        return cursor.fetchone()[0]


def test_rotation_dry_run_apply_and_checkpoint_are_resumable(tmp_path, capsys):
    active_key_id = "rotation-test-2026"
    active_key = Fernet.generate_key().decode("ascii")
    legacy_key = derive_legacy_fernet_key("test-only-secret-key")
    legacy_value = Fernet(legacy_key).encrypt(b"5511999000001").decode("ascii")
    settings = {
        "PII_ENCRYPTION_KEYRING_JSON": json.dumps({active_key_id: active_key}),
        "PII_ENCRYPTION_ACTIVE_KEY_ID": active_key_id,
    }

    with override_settings(**settings):
        student = Student.objects.create(
            full_name="Rotation Canary",
            phone="5511999000001",
            email="rotation-canary@example.test",
        )
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE boxcore_student SET phone = %s WHERE id = %s",
                [legacy_value, student.pk],
            )

        checkpoint = tmp_path / "rotation-state.json"
        call_command(
            "rotate_pii_encryption",
            schema="box_test",
            model="Student",
            field="phone",
            limit=1,
        )
        dry_run = json.loads(capsys.readouterr().out)
        assert dry_run["eligible"] == 1
        assert dry_run["would_write"] == 1
        assert _raw_student_phone(student.pk) == legacy_value

        call_command(
            "rotate_pii_encryption",
            schema="box_test",
            model="Student",
            field="phone",
            apply=True,
            limit=1,
            checkpoint=str(checkpoint),
        )
        applied = json.loads(capsys.readouterr().out)
        rotated_value = _raw_student_phone(student.pk)
        decoded = decode(rotated_value)
        assert applied["written"] == 1
        assert decoded.status == "envelope"
        assert decoded.key_id == active_key_id
        assert decoded.plaintext == "5511999000001"
        assert "5511999000001" not in checkpoint.read_text(encoding="utf-8")

        call_command(
            "rotate_pii_encryption",
            schema="box_test",
            model="Student",
            field="phone",
            apply=True,
            checkpoint=str(checkpoint),
        )
        resumed = json.loads(capsys.readouterr().out)
        assert resumed["written"] == 0
        assert resumed["rows_scanned"] == 0
        assert resumed["complete_scan"] is True
        assert _raw_student_phone(student.pk) == rotated_value

        next_key_id = "rotation-test-next"
        with override_settings(
            PII_ENCRYPTION_KEYRING_JSON=json.dumps({next_key_id: Fernet.generate_key().decode("ascii")}),
            PII_ENCRYPTION_ACTIVE_KEY_ID=next_key_id,
        ):
            with pytest.raises(CommandError, match="outro alvo ou modo"):
                call_command(
                    "rotate_pii_encryption",
                    schema="box_test",
                    model="Student",
                    field="phone",
                    apply=True,
                    checkpoint=str(checkpoint),
                )
        assert _raw_student_phone(student.pk) == rotated_value


def test_rotation_reports_unreadable_values_without_overwriting_them(tmp_path, capsys):
    active_key_id = "rotation-test-2026"
    active_key = Fernet.generate_key().decode("ascii")
    with override_settings(
        PII_ENCRYPTION_KEYRING_JSON=json.dumps({active_key_id: active_key}),
        PII_ENCRYPTION_ACTIVE_KEY_ID=active_key_id,
    ):
        student = Student.objects.create(
            full_name="Unreadable Rotation Canary",
            phone="5511999000002",
            email="rotation-invalid@example.test",
        )
        invalid_value = "gAAAAA-invalid-rotation-canary"
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE boxcore_student SET phone = %s WHERE id = %s",
                [invalid_value, student.pk],
            )

        call_command(
            "rotate_pii_encryption",
            schema="box_test",
            model="Student",
            field="phone",
            apply=True,
            limit=1,
            checkpoint=str(tmp_path / "unreadable-state.json"),
        )
        report = json.loads(capsys.readouterr().out)

        assert report["unreadable"] == 1
        assert report["written"] == 0
        assert invalid_value not in json.dumps(report)
        assert _raw_student_phone(student.pk) == invalid_value


def test_rotation_rejects_unallowlisted_field_before_reading_data():
    with pytest.raises(CommandError, match="allowlist"):
        call_command(
            "rotate_pii_encryption",
            schema="box_test",
            model="Student",
            field="email",
        )


def test_rotation_resumes_after_a_bounded_partial_batch(tmp_path, capsys):
    first_key_id = "rotation-lab-before"
    first_key = Fernet.generate_key().decode("ascii")
    legacy_key = derive_legacy_fernet_key("test-only-secret-key")
    settings = {
        "PII_ENCRYPTION_KEYRING_JSON": json.dumps({first_key_id: first_key}),
        "PII_ENCRYPTION_ACTIVE_KEY_ID": first_key_id,
    }
    with override_settings(**settings):
        students = [
            Student.objects.create(
                full_name=f"Rotation Batch Canary {suffix}",
                phone=f"55119990001{suffix:02d}",
                email=f"rotation-batch-{suffix}@example.test",
            )
            for suffix in (1, 2)
        ]
        legacy_values = {}
        with connection.cursor() as cursor:
            for student in students:
                raw_value = Fernet(legacy_key).encrypt(
                    student.phone.encode("utf-8")
                ).decode("ascii")
                legacy_values[student.pk] = raw_value
                cursor.execute(
                    "UPDATE boxcore_student SET phone = %s WHERE id = %s",
                    [raw_value, student.pk],
                )

        checkpoint = tmp_path / "interrupted-rotation.json"
        call_command(
            "rotate_pii_encryption",
            schema="box_test",
            model="Student",
            field="phone",
            apply=True,
            limit=1,
            checkpoint=str(checkpoint),
        )
        first_batch = json.loads(capsys.readouterr().out)
        assert first_batch["written"] == 1
        assert first_batch["complete_scan"] is False
        assert _raw_student_phone(students[0].pk) != legacy_values[students[0].pk]
        assert _raw_student_phone(students[1].pk) == legacy_values[students[1].pk]

        # A fresh command invocation models process interruption between batches.
        call_command(
            "rotate_pii_encryption",
            schema="box_test",
            model="Student",
            field="phone",
            apply=True,
            checkpoint=str(checkpoint),
        )
        resumed = json.loads(capsys.readouterr().out)
        assert resumed["written"] == 1
        assert resumed["complete_scan"] is True
        for student in students:
            decoded = decode(_raw_student_phone(student.pk))
            assert decoded.status == "envelope"
            assert decoded.key_id == first_key_id
            assert decoded.plaintext == student.phone

        second_key_id = "rotation-lab-after"
        second_key = Fernet.generate_key().decode("ascii")
        with override_settings(
            PII_ENCRYPTION_KEYRING_JSON=json.dumps(
                {first_key_id: first_key, second_key_id: second_key}
            ),
            PII_ENCRYPTION_ACTIVE_KEY_ID=second_key_id,
        ):
            call_command(
                "rotate_pii_encryption",
                schema="box_test",
                model="Student",
                field="phone",
                apply=True,
                checkpoint=str(tmp_path / "after-rotation.json"),
            )
            rotated = json.loads(capsys.readouterr().out)
            assert rotated["written"] == 2
            for student in students:
                decoded = decode(_raw_student_phone(student.pk))
                assert decoded.key_id == second_key_id
                assert decoded.plaintext == student.phone
