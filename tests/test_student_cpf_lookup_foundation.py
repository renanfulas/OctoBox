import json

import pytest
from django.core.management import call_command
from django.test import override_settings
from django_tenants.utils import schema_context

from shared_support.crypto_fields import generate_cpf_blind_index
from shared_support.cpf_lookup import cpf_lookup_index_is_ready
from students.models import Student


pytestmark = pytest.mark.django_db(transaction=True)


def test_student_cpf_lookup_index_is_domain_separated_and_normalized():
    assert generate_cpf_blind_index("052.484.340-68") == generate_cpf_blind_index("05248434068")
    assert generate_cpf_blind_index("12345678901") != generate_cpf_blind_index("5512345678901")


def test_student_save_dual_writes_cpf_index_with_partial_updates():
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


def test_cpf_lookup_readiness_is_tenant_scoped():
    with override_settings(CPF_LOOKUP_INDEX_READY=False, CPF_LOOKUP_INDEX_READY_BOXES=("box_test",)):
        with schema_context("box_test"):
            assert cpf_lookup_index_is_ready() is True
        with schema_context("box_other"):
            assert cpf_lookup_index_is_ready() is False
        with schema_context("public"), override_settings(CPF_LOOKUP_INDEX_READY=True):
            assert cpf_lookup_index_is_ready() is False


def test_cpf_backfill_dry_run_then_apply_is_resumable(capsys):
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

    call_command("backfill_student_cpf_lookup_index", schema="box_test", batch_size=1, apply=True)
    applied = json.loads(capsys.readouterr().out)
    student.refresh_from_db()
    assert applied["mode"] == "apply"
    assert applied["written"] == 1
    assert student.cpf_lookup_index == generate_cpf_blind_index("05248434068")
