import uuid

import pytest
from django.test import override_settings
from django_tenants.utils import get_public_schema_name, schema_context

from shared_support.crypto_fields import generate_email_blind_index
from student_identity.models import StudentIdentity, StudentIdentityProvider


pytestmark = pytest.mark.django_db


def _identity(email):
    return StudentIdentity.objects.create(
        provider=StudentIdentityProvider.GOOGLE,
        provider_subject=f"email-index-update-fields-{uuid.uuid4().hex}",
        email=email,
    )


def test_save_keeps_email_and_index_aligned_when_update_fields_excludes_email():
    key = "student-identity-email-test-key"
    original_email = "original@example.test"
    changed_email = "not-yet-persisted@example.test"

    with schema_context(get_public_schema_name()), override_settings(EMAIL_BLIND_INDEX_KEY=key):
        identity = _identity(original_email)
        original_index = generate_email_blind_index(original_email, key=key)

        identity.email = changed_email
        identity.student_name = "Updated display name"
        identity.save(update_fields=["student_name"])

        persisted = StudentIdentity.objects.get(pk=identity.pk)
        assert persisted.email == original_email
        assert persisted.email_lookup_index == original_index

        identity.save(update_fields=["email"])
        identity.refresh_from_db()

    assert identity.email == changed_email
    assert identity.email_lookup_index == generate_email_blind_index(changed_email, key=key)


def test_save_rebuilds_missing_index_when_email_is_explicitly_persisted():
    key = "student-identity-email-test-key"
    email = "rebuild-index@example.test"

    with schema_context(get_public_schema_name()), override_settings(EMAIL_BLIND_INDEX_KEY=key):
        identity = _identity(email)
        StudentIdentity.objects.filter(pk=identity.pk).update(email_lookup_index="")

        identity.save(update_fields=["email"])
        identity.refresh_from_db()

    assert identity.email_lookup_index == generate_email_blind_index(email, key=key)
