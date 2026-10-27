import json

import pytest
from django.core.management import call_command
from django.db import connection

from communications.models import WhatsAppContact, WhatsAppMessageLog
from onboarding.models import StudentIntake
from students.models import Student


pytestmark = pytest.mark.django_db(transaction=True)


def test_tenant_census_is_read_only_aggregate_and_migration_widens_storage(capsys):
    student = Student.objects.create(
        full_name="Census Canary Student",
        phone="5511998765432",
        email="census-private@example.test",
    )
    StudentIntake.objects.create(
        full_name="Census Canary Intake",
        phone="5511998765433",
        email="census-intake-private@example.test",
    )
    contact = WhatsAppContact.objects.create(phone="5511998765434")
    WhatsAppMessageLog.objects.create(contact=contact, body="private message body")

    # Corrupt only a disposable canary row through raw SQL to ensure the field
    # converter is bypassed and the census classifies without echoing it.
    invalid_token = "gAAAAA-invalid-census-canary"
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE boxcore_student SET cpf = %s WHERE id = %s",
            [invalid_token, student.pk],
        )
        cursor.execute(
            "SELECT character_maximum_length FROM information_schema.columns "
            "WHERE table_schema = current_schema() AND table_name = %s AND column_name = %s",
            ["boxcore_student", "phone"],
        )
        assert cursor.fetchone()[0] == 2048

    call_command("report_pii_encryption_formats", schema="box_test", batch_size=2)
    report = json.loads(capsys.readouterr().out)
    fields = {(row["model"], row["field"]): row for row in report["fields"]}

    assert report["schema"] == "box_test"
    assert fields[("Student", "phone")]["format_counts"] == {"legacy_fernet": 1}
    assert fields[("Student", "cpf")]["format_counts"] == {"invalid_ciphertext": 1}
    assert fields[("Student", "email")]["stored_plaintext"] is True
    assert fields[("Student", "email")]["format_counts"] == {"unencrypted_plaintext": 1}
    assert fields[("StudentIntake", "email")]["format_counts"] == {"legacy_fernet": 1}
    rendered = json.dumps(report)
    for secret_value in (
        "5511998765432",
        "5511998765433",
        "5511998765434",
        "census-private@example.test",
        "census-intake-private@example.test",
        "private message body",
        invalid_token,
    ):
        assert secret_value not in rendered

    # The command must not write or alter any canary values.
    assert (
        Student.objects.filter(pk=student.pk).values_list("email", flat=True).get()
        == "census-private@example.test"
    )
