import json

import pytest
from django.contrib import admin
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.db import connection
from django.test import override_settings
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, schema_context

from public_workouts.email_lookup import (
    checkout_leads_for_email,
    get_or_create_checkout_lead,
    get_or_create_waiting_waitlist_entry,
    waitlist_entries_for_email,
)
from public_workouts.admin import (
    PublicWorkoutCheckoutLeadAdmin,
    PublicWorkoutWaitlistEntryAdmin,
)
from public_workouts.models import (
    PublicWorkoutCheckoutLead,
    PublicWorkoutTier,
    PublicWorkoutWaitlistEntry,
    PublicWorkoutWaitlistStatus,
)
from shared_support.crypto_fields import (
    generate_public_workout_account_email_blind_index,
    generate_public_workout_checkout_lead_email_blind_index,
    generate_public_workout_waitlist_email_blind_index,
)


pytestmark = pytest.mark.django_db


def test_commerce_email_domains_are_normalized_and_purpose_separated():
    key = "commerce-email-test-key"
    email = "  Athlete@Example.Test "
    checkout = generate_public_workout_checkout_lead_email_blind_index(email, key=key)
    waitlist = generate_public_workout_waitlist_email_blind_index(email, key=key)

    assert checkout == generate_public_workout_checkout_lead_email_blind_index(
        "athlete@example.test", key=key,
    )
    assert waitlist == generate_public_workout_waitlist_email_blind_index(
        "athlete@example.test", key=key,
    )
    assert len({
        checkout,
        waitlist,
        generate_public_workout_account_email_blind_index(email, key=key),
    }) == 3


def test_commerce_models_dual_write_with_partial_update_fields():
    key = "commerce-email-test-key"
    with override_settings(EMAIL_BLIND_INDEX_KEY=key), schema_context(get_public_schema_name()):
        lead = PublicWorkoutCheckoutLead.objects.create(
            email="lead@example.test", tier=PublicWorkoutTier.ESSENCIAL,
        )
        entry = PublicWorkoutWaitlistEntry.objects.create(
            email="wait@example.test", tier=PublicWorkoutTier.ESSENCIAL,
        )
        lead.email = "Lead2@Example.Test"
        lead.save(update_fields=["email", "updated_at"])
        entry.email = "Wait2@Example.Test"
        entry.save(update_fields=["email", "updated_at"])
        lead.refresh_from_db()
        entry.refresh_from_db()

    assert lead.email_lookup_index == generate_public_workout_checkout_lead_email_blind_index(
        lead.email, key=key,
    )
    assert entry.email_lookup_index == generate_public_workout_waitlist_email_blind_index(
        entry.email, key=key,
    )


def test_commerce_models_keep_email_indexes_aligned_across_partial_updates():
    key = "commerce-email-test-key"
    old_lead_email = "lead-before-partial@example.test"
    new_lead_email = "lead-after-partial@example.test"
    old_waitlist_email = "wait-before-partial@example.test"
    new_waitlist_email = "wait-after-partial@example.test"
    with override_settings(EMAIL_BLIND_INDEX_KEY=key), schema_context(get_public_schema_name()):
        lead = PublicWorkoutCheckoutLead.objects.create(
            email=old_lead_email,
            tier=PublicWorkoutTier.ESSENCIAL,
        )
        entry = PublicWorkoutWaitlistEntry.objects.create(
            email=old_waitlist_email,
            tier=PublicWorkoutTier.ESSENCIAL,
        )
        old_lead_index = generate_public_workout_checkout_lead_email_blind_index(
            old_lead_email, key=key,
        )
        old_waitlist_index = generate_public_workout_waitlist_email_blind_index(
            old_waitlist_email, key=key,
        )

        lead.email = new_lead_email
        lead.save(update_fields=["updated_at"])
        entry.email = new_waitlist_email
        entry.save(update_fields=["updated_at"])

        persisted_lead = PublicWorkoutCheckoutLead.objects.get(pk=lead.pk)
        persisted_entry = PublicWorkoutWaitlistEntry.objects.get(pk=entry.pk)
        assert persisted_lead.email == old_lead_email
        assert persisted_lead.email_lookup_index == old_lead_index
        assert persisted_entry.email == old_waitlist_email
        assert persisted_entry.email_lookup_index == old_waitlist_index

        lead.save(update_fields=["email"])
        entry.save(update_fields=["email"])
        lead.refresh_from_db()
        entry.refresh_from_db()

    assert lead.email == new_lead_email
    assert lead.email_lookup_index == generate_public_workout_checkout_lead_email_blind_index(
        new_lead_email, key=key,
    )
    assert entry.email == new_waitlist_email
    assert entry.email_lookup_index == generate_public_workout_waitlist_email_blind_index(
        new_waitlist_email, key=key,
    )


def test_readers_support_legacy_mode_and_revalidate_hmac_candidates():
    key = "commerce-email-test-key"
    with schema_context(get_public_schema_name()):
        target_lead = PublicWorkoutCheckoutLead.objects.create(
            email="Target@Example.Test", tier=PublicWorkoutTier.ESSENCIAL,
        )
        PublicWorkoutCheckoutLead.objects.create(
            email="other@example.test", tier=PublicWorkoutTier.ESSENCIAL,
        )
        target_waitlist = PublicWorkoutWaitlistEntry.objects.create(
            email="Target@Example.Test", tier=PublicWorkoutTier.ESSENCIAL,
        )
        PublicWorkoutWaitlistEntry.objects.create(
            email="other@example.test", tier=PublicWorkoutTier.ESSENCIAL,
        )
        PublicWorkoutCheckoutLead.objects.filter(pk=target_lead.pk).update(
            email_lookup_index=generate_public_workout_checkout_lead_email_blind_index(
                target_lead.email, key=key,
            ),
        )
        PublicWorkoutCheckoutLead.objects.filter(email="other@example.test").update(
            email_lookup_index=generate_public_workout_checkout_lead_email_blind_index(
                target_lead.email, key=key,
            ),
        )
        PublicWorkoutWaitlistEntry.objects.filter(pk=target_waitlist.pk).update(
            email_lookup_index=generate_public_workout_waitlist_email_blind_index(
                target_waitlist.email, key=key,
            ),
        )
        PublicWorkoutWaitlistEntry.objects.filter(email="other@example.test").update(
            email_lookup_index=generate_public_workout_waitlist_email_blind_index(
                target_waitlist.email, key=key,
            ),
        )
        with override_settings(
            PUBLIC_WORKOUT_CHECKOUT_LEAD_EMAIL_LOOKUP_INDEX_READY=False,
            PUBLIC_WORKOUT_WAITLIST_EMAIL_LOOKUP_INDEX_READY=False,
        ):
            assert [x.pk for x in checkout_leads_for_email("target@example.test")] == [target_lead.pk]
            assert [x.pk for x in waitlist_entries_for_email("target@example.test")] == [target_waitlist.pk]
        with override_settings(
            PUBLIC_WORKOUT_CHECKOUT_LEAD_EMAIL_LOOKUP_INDEX_READY=True,
            PUBLIC_WORKOUT_WAITLIST_EMAIL_LOOKUP_INDEX_READY=True,
            EMAIL_BLIND_INDEX_KEY=key,
        ):
            assert [x.pk for x in checkout_leads_for_email(" target@example.test ")] == [target_lead.pk]
            assert [x.pk for x in waitlist_entries_for_email(" target@example.test ")] == [target_waitlist.pk]


def test_active_commerce_email_readers_fail_closed_without_key():
    with override_settings(
        PUBLIC_WORKOUT_CHECKOUT_LEAD_EMAIL_LOOKUP_INDEX_READY=True,
        PUBLIC_WORKOUT_WAITLIST_EMAIL_LOOKUP_INDEX_READY=True,
        EMAIL_BLIND_INDEX_KEY="",
    ):
        with pytest.raises(ImproperlyConfigured):
            checkout_leads_for_email("person@example.test")
        with pytest.raises(ImproperlyConfigured):
            waitlist_entries_for_email("person@example.test")


@pytest.mark.parametrize("indexed", [False, True], ids=["legacy", "hmac"])
def test_commerce_admin_email_search_is_exact_in_legacy_and_indexed_modes(indexed):
    key = "commerce-email-test-key"
    with schema_context(get_public_schema_name()), override_settings(
        PUBLIC_WORKOUT_CHECKOUT_LEAD_EMAIL_LOOKUP_INDEX_READY=indexed,
        PUBLIC_WORKOUT_WAITLIST_EMAIL_LOOKUP_INDEX_READY=indexed,
        EMAIL_BLIND_INDEX_KEY=key if indexed else "",
    ):
        target_lead = PublicWorkoutCheckoutLead.objects.create(
            email="Target@Example.Test", tier=PublicWorkoutTier.ESSENCIAL,
        )
        PublicWorkoutCheckoutLead.objects.create(
            email="targeted@example.test", tier=PublicWorkoutTier.PREMIUM,
        )
        target_waitlist = PublicWorkoutWaitlistEntry.objects.create(
            email="Target@Example.Test", tier=PublicWorkoutTier.ESSENCIAL,
        )
        PublicWorkoutWaitlistEntry.objects.create(
            email="targeted@example.test", tier=PublicWorkoutTier.ESSENCIAL,
        )

        lead_admin = PublicWorkoutCheckoutLeadAdmin(PublicWorkoutCheckoutLead, admin.site)
        waitlist_admin = PublicWorkoutWaitlistEntryAdmin(PublicWorkoutWaitlistEntry, admin.site)
        lead_results, lead_distinct = lead_admin.get_search_results(
            None, PublicWorkoutCheckoutLead.objects.all(), " target@example.test ",
        )
        waitlist_results, waitlist_distinct = waitlist_admin.get_search_results(
            None, PublicWorkoutWaitlistEntry.objects.all(), " target@example.test ",
        )
        partial_lead_results, _ = lead_admin.get_search_results(
            None, PublicWorkoutCheckoutLead.objects.all(), "target@example",
        )
        partial_waitlist_results, _ = waitlist_admin.get_search_results(
            None, PublicWorkoutWaitlistEntry.objects.all(), "target@example",
        )

    assert list(lead_results.values_list("pk", flat=True)) == [target_lead.pk]
    assert list(waitlist_results.values_list("pk", flat=True)) == [target_waitlist.pk]
    assert lead_distinct is False and waitlist_distinct is False
    assert not partial_lead_results.exists()
    assert not partial_waitlist_results.exists()


def test_get_or_create_commerce_rows_are_normalized_and_idempotent():
    with schema_context(get_public_schema_name()):
        first_lead, lead_created = get_or_create_checkout_lead(
            email="Lead@Example.Test", defaults={"tier": PublicWorkoutTier.ESSENCIAL},
        )
        second_lead, duplicate_lead_created = get_or_create_checkout_lead(
            email=" lead@example.test ", defaults={"tier": PublicWorkoutTier.PREMIUM},
        )
        first_entry, entry_created = get_or_create_waiting_waitlist_entry(
            email="Wait@Example.Test", tier=PublicWorkoutTier.ESSENCIAL,
        )
        second_entry, duplicate_entry_created = get_or_create_waiting_waitlist_entry(
            email=" wait@example.test ", tier=PublicWorkoutTier.ESSENCIAL,
        )

    assert lead_created is True and duplicate_lead_created is False
    assert first_lead.pk == second_lead.pk
    assert second_lead.tier == PublicWorkoutTier.ESSENCIAL
    assert first_entry.email == "wait@example.test"
    assert entry_created is True and duplicate_entry_created is False
    assert first_entry.pk == second_entry.pk


def test_commerce_backfill_counts_only_active_unique_predicate_groups(capsys):
    schema = get_public_schema_name()
    with schema_context(schema):
        first_lead = PublicWorkoutCheckoutLead.objects.create(
            email="dupe@example.test", tier=PublicWorkoutTier.ESSENCIAL,
        )
        paid_lead = PublicWorkoutCheckoutLead.objects.create(
            email="dupe@example.test", tier=PublicWorkoutTier.PREMIUM,
            paid_at=timezone.now(),
        )
        first_wait = PublicWorkoutWaitlistEntry.objects.create(
            email="same@example.test", tier=PublicWorkoutTier.ESSENCIAL,
        )
        other_tier = PublicWorkoutWaitlistEntry.objects.create(
            email="same@example.test", tier=PublicWorkoutTier.PREMIUM,
        )
        invited = PublicWorkoutWaitlistEntry.objects.create(
            email="same@example.test", tier=PublicWorkoutTier.ESSENCIAL,
            status=PublicWorkoutWaitlistStatus.INVITED,
        )
        assert PublicWorkoutCheckoutLead._meta.get_field("email_lookup_index").db_type(connection) == "varchar(67)"
        assert PublicWorkoutWaitlistEntry._meta.get_field("email_lookup_index").db_type(connection) == "varchar(67)"

    key = "commerce-email-test-key"
    with override_settings(EMAIL_BLIND_INDEX_KEY=key):
        call_command("backfill_public_workout_commerce_email_lookup_indexes", batch_size=2)
        dry_run = json.loads(capsys.readouterr().out)
        assert dry_run["mode"] == "dry-run"
        assert dry_run["checkout_leads"]["written"] == 0
        call_command("backfill_public_workout_commerce_email_lookup_indexes", apply=True, batch_size=2)
        applied = json.loads(capsys.readouterr().out)
        assert applied["checkout_leads"]["written"] >= 2
        call_command("backfill_public_workout_commerce_email_lookup_indexes", verify=True, batch_size=2)
        verified = json.loads(capsys.readouterr().out)

    assert verified["verification_clean"] is True
    assert verified["active_uniqueness_duplicate_groups"] == {
        "unpaid_checkout_lead_email": 0,
        "waiting_waitlist_email_tier": 0,
    }
    assert len({first_lead.pk, paid_lead.pk}) == 2
    assert len({first_wait.pk, other_tier.pk, invited.pk}) == 3
    assert "dupe@example.test" not in json.dumps([dry_run, applied, verified])
    assert "same@example.test" not in json.dumps([dry_run, applied, verified])
