import json
import logging

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.test import override_settings
from django_tenants.utils import schema_context

from catalog.forms import StudentQuickForm
from operations.services.student_importer import StudentImporter, _build_error_row
from shared_support.crypto_fields import generate_blind_index, generate_cpf_blind_index
from shared_support.cpf_lookup import cpf_lookup_index_is_ready
from students.models import Student


pytestmark = pytest.mark.django_db(transaction=True)


def test_cpf_lookup_readiness_can_be_enabled_per_tenant_only():
    with override_settings(
        CPF_LOOKUP_INDEX_READY=False,
        CPF_LOOKUP_INDEX_READY_BOXES=("box_test",),
    ):
        with schema_context("box_test"):
            assert cpf_lookup_index_is_ready() is True
        with schema_context("box_other"):
            assert cpf_lookup_index_is_ready() is False
        with schema_context("public"), override_settings(CPF_LOOKUP_INDEX_READY=True):
            assert cpf_lookup_index_is_ready() is False


def test_student_save_dual_writes_cpf_index_when_cpf_changes_with_update_fields():
    student = Student.objects.create(
        full_name="CPF Index Student",
        phone="5511998765001",
        cpf="052.484.340-68",
    )
    original_index = student.cpf_lookup_index
    assert original_index == generate_cpf_blind_index("05248434068")

    student.cpf = "111.444.777-35"
    student.save(update_fields=["cpf", "updated_at"])
    student.refresh_from_db()

    assert student.cpf_lookup_index == generate_cpf_blind_index("11144477735")
    assert student.cpf_lookup_index != original_index


def test_student_save_keeps_phone_and_cpf_indexes_with_their_source_fields():
    old_phone = "5511998765091"
    new_phone = "5511998765092"
    old_cpf = "052.484.340-68"
    new_cpf = "111.444.777-35"
    student = Student.objects.create(
        full_name="Partial Update Index Student",
        phone=old_phone,
        cpf=old_cpf,
    )
    old_phone_index = generate_blind_index(old_phone)
    old_cpf_index = generate_cpf_blind_index(old_cpf)

    student.phone = new_phone
    student.cpf = new_cpf
    student.full_name = "Name Only Update"
    student.save(update_fields=["full_name"])

    persisted = Student.objects.get(pk=student.pk)
    assert persisted.full_name == "Name Only Update"
    assert persisted.phone == old_phone
    assert persisted.phone_lookup_index == old_phone_index
    assert persisted.cpf == old_cpf
    assert persisted.cpf_lookup_index == old_cpf_index

    student.save(update_fields=["phone", "cpf"])
    student.refresh_from_db()

    assert student.phone == new_phone
    assert student.phone_lookup_index == generate_blind_index(new_phone)
    assert student.cpf == new_cpf
    assert student.cpf_lookup_index == generate_cpf_blind_index(new_cpf)


def test_quick_form_checks_cpf_duplicate_by_index():
    Student.objects.create(
        full_name="CPF Existing Student",
        phone="5511998765002",
        cpf="052.484.340-68",
    )
    form = StudentQuickForm(instance=Student())
    form.cleaned_data = {"cpf": "05248434068"}

    with pytest.raises(ValidationError, match="Já existe um aluno cadastrado com este CPF"):
        form.clean_cpf()


def test_quick_form_blocks_cpf_until_index_backfill_is_enabled():
    form = StudentQuickForm(instance=Student())
    form.cleaned_data = {"cpf": "05248434068"}

    with override_settings(CPF_LOOKUP_INDEX_READY=False):
        with pytest.raises(ValidationError, match="validação segura de CPF ainda não está disponível"):
            form.clean_cpf()


def test_cpf_index_command_is_read_only_by_default_then_backfills_and_verifies(capsys):
    student = Student.objects.create(
        full_name="CPF Backfill Canary",
        phone="5511998765003",
        cpf="052.484.340-68",
    )
    Student.objects.filter(pk=student.pk).update(cpf_lookup_index="")

    call_command("backfill_student_cpf_lookup_index", schema="box_test", batch_size=1)
    dry_run = json.loads(capsys.readouterr().out)
    assert dry_run["mode"] == "dry-run"
    assert dry_run["missing_index"] == 1
    assert dry_run["written"] == 0
    assert Student.objects.filter(pk=student.pk, cpf_lookup_index="").exists()

    call_command(
        "backfill_student_cpf_lookup_index",
        schema="box_test",
        batch_size=1,
        apply=True,
    )
    applied = json.loads(capsys.readouterr().out)
    assert applied["mode"] == "apply"
    assert applied["written"] == 1
    assert Student.objects.get(pk=student.pk).cpf_lookup_index == generate_cpf_blind_index(
        "05248434068"
    )

    call_command("backfill_student_cpf_lookup_index", schema="box_test", verify=True)
    verified = json.loads(capsys.readouterr().out)
    assert verified["mode"] == "verify"
    assert verified["missing_index"] == 0
    assert verified["drift"] == 0
    assert "05248434068" not in json.dumps(dry_run | applied | verified)


def test_cpf_index_command_fails_closed_on_unreadable_ciphertext(capsys):
    student = Student.objects.create(
        full_name="CPF Unreadable Canary",
        phone="5511998765004",
    )
    invalid_token = "gAAAAA-private-cpf-canary"
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE boxcore_student SET cpf = %s WHERE id = %s",
            [invalid_token, student.pk],
        )

    with pytest.raises(CommandError, match="nenhum valor de CPF foi exibido"):
        call_command(
            "backfill_student_cpf_lookup_index",
            schema="box_test",
            apply=True,
        )
    assert invalid_token not in capsys.readouterr().err


def test_cpf_index_command_reports_legacy_duplicate_groups_before_verify_accepts(capsys):
    cpf = "052.484.340-68"
    first = Student.objects.create(
        full_name="CPF Duplicate One",
        phone="5511998765011",
        cpf=cpf,
    )
    second = Student.objects.create(
        full_name="CPF Duplicate Two",
        phone="5511998765012",
        cpf=cpf,
    )
    Student.objects.filter(pk__in=[first.pk, second.pk]).update(cpf_lookup_index="")

    call_command(
        "backfill_student_cpf_lookup_index",
        schema="box_test",
        apply=True,
        batch_size=1,
    )
    applied = json.loads(capsys.readouterr().out)
    assert applied["written"] == 2
    assert applied["stored_duplicate_index_groups"] == 1
    assert applied["complete_target_scan"] is True

    with pytest.raises(CommandError, match="índice ausente, divergente ou duplicado"):
        call_command(
            "backfill_student_cpf_lookup_index",
            schema="box_test",
            verify=True,
            batch_size=1,
        )
    verification = json.loads(capsys.readouterr().out)
    assert verification["missing_index"] == 0
    assert verification["drift"] == 0
    assert verification["stored_duplicate_index_groups"] == 1


def test_student_csv_import_dual_writes_phone_and_cpf_indexes_on_create(tmp_path):
    csv_path = tmp_path / "students.csv"
    csv_path.write_text(
        "full_name,phone,cpf\nCSV Student,5511998765021,052.484.340-68\n",
        encoding="utf-8",
    )

    report = StudentImporter(batch_size=10).import_from_file(str(csv_path))
    student = Student.objects.get(phone_lookup_index=generate_blind_index("11998765021"))

    assert report["success"] == 1
    assert student.phone_lookup_index == generate_blind_index("11998765021")
    assert student.cpf_lookup_index == generate_cpf_blind_index("05248434068")


def test_student_csv_import_updates_cpf_and_its_index_in_bulk(tmp_path):
    student = Student.objects.create(
        full_name="Existing CSV Student",
        phone="11998765022",
        cpf="052.484.340-68",
    )
    original_index = student.cpf_lookup_index
    csv_path = tmp_path / "students-update.csv"
    csv_path.write_text(
        "full_name,phone,cpf\nUpdated CSV Student,5511998765022,111.444.777-35\n",
        encoding="utf-8",
    )

    with CaptureQueriesContext(connection) as captured:
        report = StudentImporter(batch_size=10).import_from_file(str(csv_path))
    student.refresh_from_db()

    assert report["updated"] == 1
    assert student.full_name == "Updated CSV Student"
    assert student.phone_lookup_index == generate_blind_index("11998765022")
    assert student.cpf_lookup_index == generate_cpf_blind_index("11144477735")
    assert student.cpf_lookup_index != original_index
    executed_sql = "\n".join(query["sql"].lower() for query in captured)
    assert "phone_lookup_index" in executed_sql
    assert '"boxcore_student"."phone"' not in executed_sql


def test_student_csv_import_requires_blind_index_key_before_writing(tmp_path):
    csv_path = tmp_path / "students-no-blind-index.csv"
    csv_path.write_text(
        "full_name,phone\nShould Not Be Written,5511998765023\n",
        encoding="utf-8",
    )

    with override_settings(PHONE_BLIND_INDEX_KEY=""):
        with pytest.raises(ValueError, match="PHONE_BLIND_INDEX_KEY is required"):
            StudentImporter(batch_size=10).import_from_file(str(csv_path))

    assert not Student.objects.filter(phone_lookup_index=generate_blind_index("11998765023")).exists()


def test_student_import_failure_log_omits_file_name_and_exception_text(tmp_path, caplog):
    marker = 'sensitive-student-5511998765025@example.test'
    csv_path = tmp_path / f'{marker}.csv'
    csv_path.write_text('full_name,phone\nStudent,5511998765025\n', encoding='utf-8')

    with override_settings(PHONE_BLIND_INDEX_KEY=""), caplog.at_level(logging.ERROR, logger='octobox.students'):
        with pytest.raises(ValueError, match="PHONE_BLIND_INDEX_KEY is required"):
            StudentImporter(batch_size=10).import_from_file(str(csv_path))

    assert marker not in caplog.text
    assert 'job_execution_failed' in caplog.text


def test_student_import_failure_cache_payload_omits_pii_and_exception_text():
    phone = "5511998765024"
    name = "Sensitive Student Name"
    failure = _build_error_row(17, Student(full_name=name, phone=phone), ValueError(phone))

    assert failure == {
        "line": 17,
        "error": "Falha ao processar esta linha; revise os dados e tente novamente.",
    }
    assert phone not in json.dumps(failure)
    assert name not in json.dumps(failure)
