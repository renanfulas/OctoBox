import os
import unittest

import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")

import django

django.setup()

from django.contrib import admin
from django.test import RequestFactory, SimpleTestCase

from communications.admin import (
    StudentIntakeAdmin,
    WhatsAppContactAdmin,
    WhatsAppMessageLogAdmin,
)
from communications.models import StudentIntake, WhatsAppContact, WhatsAppMessageLog
from communications.queries import get_unlinked_whatsapp_contacts
from finance.admin import EnrollmentAdmin, PaymentAdmin
from finance.models import Enrollment, Payment
from operations.admin import AttendanceAdmin
from operations.models import Attendance
from shared_support.crypto_fields import generate_blind_index
from student_identity.admin import (
    StudentIdentityAdmin,
    StudentInvitationDeliveryEventAdmin,
    StudentTransferAdmin,
)
from student_identity.models import (
    StudentIdentity,
    StudentInvitationDeliveryEvent,
    StudentTransfer,
)
from students.admin import StudentAdmin
from students.models import Student


class EncryptedAdminSearchTests(SimpleTestCase):
    def _search_sql(self, model_admin, model, term):
        request = RequestFactory().get("/admin/", {"q": term})
        queryset, may_have_duplicates = model_admin.get_search_results(
            request,
            model.objects.all(),
            term,
        )
        sql, params = queryset.query.sql_with_params()
        where = sql.partition(" WHERE ")[2].partition(" ORDER BY ")[0]
        return where, params, may_have_duplicates

    def test_student_admin_uses_exact_phone_blind_index_and_plain_email_search(self):
        model_admin = StudentAdmin(Student, admin.site)
        self.assertEqual(model_admin.phone_lookup_path, "phone_lookup_index")
        self.assertEqual(model_admin.search_fields, ("full_name", "email"))

        where, params, _ = self._search_sql(model_admin, Student, "+55 (11) 99999-1111")
        self.assertIn('"phone_lookup_index"', where)
        self.assertIn(generate_blind_index("11999991111"), params)

    def test_student_identity_admin_search_uses_stored_display_name(self):
        model_admin = StudentIdentityAdmin(StudentIdentity, admin.site)
        self.assertEqual(
            model_admin.search_fields,
            ("student_name", "email", "provider_subject"),
        )

        where, _, may_have_duplicates = self._search_sql(
            model_admin,
            StudentIdentity,
            "alice",
        )

        self.assertIn('"student_name"', where)
        self.assertIn('"email"', where)
        self.assertIn('"provider_subject"', where)
        self.assertNotIn('"student_id"', where)
        self.assertFalse(may_have_duplicates)

    def test_student_transfer_admin_search_uses_identity_snapshot(self):
        model_admin = StudentTransferAdmin(StudentTransfer, admin.site)
        self.assertEqual(model_admin.search_fields, ("identity__student_name", "reason"))

        where, _, may_have_duplicates = self._search_sql(
            model_admin,
            StudentTransfer,
            "alice",
        )

        self.assertIn('"student_name"', where)
        self.assertIn('"reason"', where)
        self.assertFalse(may_have_duplicates)

    def test_invitation_delivery_event_admin_uses_invitation_name_snapshot(self):
        model_admin = StudentInvitationDeliveryEventAdmin(
            StudentInvitationDeliveryEvent,
            admin.site,
        )
        self.assertEqual(
            model_admin.search_fields,
            ("delivery__invitation__student_name", "provider_event_id", "event_type"),
        )

        where, _, may_have_duplicates = self._search_sql(
            model_admin,
            StudentInvitationDeliveryEvent,
            "alice",
        )

        self.assertIn('"student_name"', where)
        self.assertIn('"provider_event_id"', where)
        self.assertIn('"event_type"', where)
        self.assertFalse(may_have_duplicates)

    def test_intake_admin_does_not_search_ciphertext_or_keep_its_useless_index(self):
        model_admin = StudentIntakeAdmin(StudentIntake, admin.site)
        self.assertEqual(model_admin.search_fields, ("full_name",))
        self.assertFalse(StudentIntake._meta.get_field("phone").db_index)
        self.assertFalse(StudentIntake._meta.get_field("email").db_index)
        self.assertFalse(Student._meta.get_field("phone").unique)
        self.assertFalse(WhatsAppContact._meta.get_field("phone").unique)

        where, params, _ = self._search_sql(model_admin, StudentIntake, "lead@example.test")
        self.assertNotIn('"email"', where)
        self.assertNotIn('"phone"', where)
        self.assertNotIn("lead@example.test", params)

    def test_related_admin_phone_searches_use_the_related_blind_index(self):
        cases = [
            (EnrollmentAdmin(Enrollment, admin.site), Enrollment, "student__phone_lookup_index"),
            (PaymentAdmin(Payment, admin.site), Payment, "student__phone_lookup_index"),
            (AttendanceAdmin(Attendance, admin.site), Attendance, "student__phone_lookup_index"),
            (WhatsAppMessageLogAdmin(WhatsAppMessageLog, admin.site), WhatsAppMessageLog, "contact__phone_lookup_index"),
        ]
        for model_admin, model, expected_path in cases:
            with self.subTest(admin=model_admin.__class__.__name__):
                self.assertEqual(model_admin.phone_lookup_path, expected_path)
                where, params, _ = self._search_sql(model_admin, model, "11999991111")
                self.assertIn('"phone_lookup_index"', where)
                self.assertIn(generate_blind_index("11999991111"), params)

    def test_whatsapp_admin_does_not_use_encrypted_text_as_search_field(self):
        contact_admin = WhatsAppContactAdmin(WhatsAppContact, admin.site)
        log_admin = WhatsAppMessageLogAdmin(WhatsAppMessageLog, admin.site)
        self.assertNotIn("phone", contact_admin.search_fields)
        self.assertNotIn("contact__phone", log_admin.search_fields)
        self.assertNotIn("body", log_admin.search_fields)

    def test_whatsapp_contact_default_ordering_does_not_use_ciphertext(self):
        contact_admin = WhatsAppContactAdmin(WhatsAppContact, admin.site)
        self.assertEqual(WhatsAppContact._meta.ordering, ["display_name", "pk"])

        queryset = contact_admin.get_queryset(RequestFactory().get("/admin/"))
        sql = str(queryset.query)
        order_by = sql.partition(" ORDER BY ")[2]
        self.assertIn('"display_name"', order_by)
        self.assertIn('"id"', order_by)
        self.assertNotIn('"phone"', order_by)

    def test_non_phone_terms_do_not_add_blind_index_predicate(self):
        model_admin = StudentAdmin(Student, admin.site)
        where, params, _ = self._search_sql(model_admin, Student, "ana 123")
        self.assertNotIn('"phone_lookup_index"', where)


@pytest.mark.django_db
def test_student_admin_exact_phone_search_returns_record_by_blind_index():
    phone = "11977773333"
    student = Student.objects.create(
        full_name="Encrypted Phone Search",
        phone=phone,
        email="search@example.test",
    )
    model_admin = StudentAdmin(Student, admin.site)
    request = RequestFactory().get("/admin/", {"q": "+55 (11) 97777-3333"})

    results, _ = model_admin.get_search_results(
        request,
        Student.objects.all(),
        "+55 (11) 97777-3333",
    )

    assert list(results) == [student]


@pytest.mark.django_db
def test_intake_email_search_is_not_claimed_but_exact_phone_search_works():
    intake = StudentIntake.objects.create(
        full_name="Encrypted Intake Search",
        phone="11977774444",
        email="private-intake@example.test",
    )
    model_admin = StudentIntakeAdmin(StudentIntake, admin.site)
    email_request = RequestFactory().get("/admin/", {"q": "private-intake@example.test"})
    phone_request = RequestFactory().get("/admin/", {"q": "11977774444"})

    email_results, _ = model_admin.get_search_results(
        email_request,
        StudentIntake.objects.all(),
        "private-intake@example.test",
    )
    phone_results, _ = model_admin.get_search_results(
        phone_request,
        StudentIntake.objects.all(),
        "11977774444",
    )

    assert list(email_results) == []
    assert list(phone_results) == [intake]


@pytest.mark.django_db
def test_unlinked_whatsapp_contacts_do_not_order_by_randomized_ciphertext():
    queryset = get_unlinked_whatsapp_contacts()

    assert queryset.query.order_by == ("display_name", "pk")


if __name__ == "__main__":
    unittest.main()
