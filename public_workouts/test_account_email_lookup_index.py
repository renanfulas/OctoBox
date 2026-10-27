import json

import pytest
from django.contrib import admin
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.db import connection
from django.test import override_settings
from django_tenants.utils import get_public_schema_name, schema_context

from public_workouts.account_email_lookup import (
    get_or_create_public_workout_account,
    public_workout_accounts_for_email,
)
from public_workouts.admin import (
    PublicWorkoutAccountAdmin,
    PublicWorkoutMealPlanAdmin,
    PublicWorkoutNutritionProfileAdmin,
    PublicWorkoutProgramDraftAdmin,
    PublicWorkoutRefundRequestAdmin,
    PublicWorkoutSubscriptionAdmin,
    PublicWorkoutTestimonialAdmin,
    PublicWorkoutWorkItemAdmin,
)
from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutMealPlan,
    PublicWorkoutNutritionProfile,
    PublicWorkoutProgramDraft,
    PublicWorkoutRefundRequest,
    PublicWorkoutSubscription,
    PublicWorkoutTestimonial,
    PublicWorkoutTier,
    PublicWorkoutWorkItem,
)
from public_workouts.views import _sort_coach_roster_rows_by_account_email
from shared_support.crypto_fields import (
    generate_email_blind_index,
    generate_public_workout_account_email_blind_index,
)


pytestmark = pytest.mark.django_db


def test_account_email_blind_index_is_normalized_and_domain_separated():
    key = "account-email-test-key"
    first = generate_public_workout_account_email_blind_index(
        "  Athlete@Example.Test ", key=key,
    )
    second = generate_public_workout_account_email_blind_index(
        "athlete@example.test", key=key,
    )

    assert first == second
    assert first.startswith("v1:")
    assert first != generate_email_blind_index("athlete@example.test", key=key)


def test_account_save_dual_writes_email_index_with_update_fields():
    key = "account-email-test-key"
    with override_settings(EMAIL_BLIND_INDEX_KEY=key), schema_context(get_public_schema_name()):
        account = PublicWorkoutAccount.objects.create(email="first@example.test")
        assert account.email_lookup_index == generate_public_workout_account_email_blind_index(
            "first@example.test", key=key,
        )

        account.email = "Second@Example.Test"
        account.save(update_fields=["email", "updated_at"])
        account.refresh_from_db()

    assert account.email == "Second@Example.Test"
    assert account.email_lookup_index == generate_public_workout_account_email_blind_index(
        "second@example.test", key=key,
    )


def test_account_save_keeps_email_and_index_aligned_across_partial_updates():
    key = "account-email-test-key"
    old_email = "before-partial@example.test"
    new_email = "after-partial@example.test"
    with override_settings(EMAIL_BLIND_INDEX_KEY=key), schema_context(get_public_schema_name()):
        account = PublicWorkoutAccount.objects.create(email=old_email)
        old_index = generate_public_workout_account_email_blind_index(old_email, key=key)
        account.email = new_email
        account.save(update_fields=["updated_at"])

        persisted = PublicWorkoutAccount.objects.get(pk=account.pk)
        assert persisted.email == old_email
        assert persisted.email_lookup_index == old_index

        account.save(update_fields=["email"])
        account.refresh_from_db()

    assert account.email == new_email
    assert account.email_lookup_index == generate_public_workout_account_email_blind_index(
        new_email, key=key,
    )


def test_email_lookup_preserves_legacy_mode_and_revalidates_index_candidates():
    key = "account-email-test-key"
    with schema_context(get_public_schema_name()):
        account = PublicWorkoutAccount.objects.create(email="Target@Example.Test")
        decoy = PublicWorkoutAccount.objects.create(email="different@example.test")
        account.email_lookup_index = generate_public_workout_account_email_blind_index(
            account.email, key=key,
        )
        account.save(update_fields=["email_lookup_index", "updated_at"])
        decoy.email_lookup_index = account.email_lookup_index
        decoy.save(update_fields=["email_lookup_index", "updated_at"])

        with override_settings(PUBLIC_WORKOUT_ACCOUNT_EMAIL_LOOKUP_INDEX_READY=False):
            assert [row.pk for row in public_workout_accounts_for_email("target@example.test")] == [account.pk]

        with override_settings(
            PUBLIC_WORKOUT_ACCOUNT_EMAIL_LOOKUP_INDEX_READY=True,
            EMAIL_BLIND_INDEX_KEY=key,
        ):
            matches = public_workout_accounts_for_email(" target@example.test ")

    assert [row.pk for row in matches] == [account.pk]


def test_active_email_lookup_fails_closed_without_key():
    with override_settings(
        PUBLIC_WORKOUT_ACCOUNT_EMAIL_LOOKUP_INDEX_READY=True,
        EMAIL_BLIND_INDEX_KEY="",
    ):
        with pytest.raises(ImproperlyConfigured):
            public_workout_accounts_for_email("person@example.test")


def test_account_admin_email_search_is_exact_in_legacy_and_indexed_modes():
    key = "account-email-test-key"
    with schema_context(get_public_schema_name()), override_settings(
        EMAIL_BLIND_INDEX_KEY=key,
        PUBLIC_WORKOUT_ACCOUNT_EMAIL_LOOKUP_INDEX_READY=False,
    ):
        target = PublicWorkoutAccount.objects.create(email="Athlete@Example.Test")
        adjacent = PublicWorkoutAccount.objects.create(email="athlete-two@example.test")
        account_admin = PublicWorkoutAccountAdmin(PublicWorkoutAccount, admin.site)
        legacy_exact, _ = account_admin.get_search_results(
            None, PublicWorkoutAccount.objects.all(), "athlete@example.test",
        )
        legacy_partial, _ = account_admin.get_search_results(
            None, PublicWorkoutAccount.objects.all(), "athlete",
        )
        with override_settings(PUBLIC_WORKOUT_ACCOUNT_EMAIL_LOOKUP_INDEX_READY=True):
            indexed_exact, _ = account_admin.get_search_results(
                None, PublicWorkoutAccount.objects.all(), "ATHLETE@example.test",
            )

    assert list(legacy_exact.values_list("pk", flat=True)) == [target.pk]
    assert list(legacy_partial.values_list("pk", flat=True)) == []
    assert list(indexed_exact.values_list("pk", flat=True)) == [target.pk]
    assert adjacent.pk not in list(indexed_exact.values_list("pk", flat=True))


def test_subscription_admin_keeps_plan_slug_partial_and_email_exact():
    key = "account-email-test-key"
    with schema_context(get_public_schema_name()), override_settings(
        EMAIL_BLIND_INDEX_KEY=key,
        PUBLIC_WORKOUT_ACCOUNT_EMAIL_LOOKUP_INDEX_READY=True,
    ):
        account = PublicWorkoutAccount.objects.create(email="athlete@example.test")
        other_account = PublicWorkoutAccount.objects.create(email="other@example.test")
        subscription = PublicWorkoutSubscription.objects.create(
            account=account,
            plan_slug="bruno-upper-lower",
            tier=PublicWorkoutTier.ESSENCIAL,
        )
        other_subscription = PublicWorkoutSubscription.objects.create(
            account=other_account,
            plan_slug="giovanna-legs",
            tier=PublicWorkoutTier.ESSENCIAL,
        )
        subscription_admin = PublicWorkoutSubscriptionAdmin(
            PublicWorkoutSubscription,
            admin.site,
        )
        exact_email, _ = subscription_admin.get_search_results(
            None,
            PublicWorkoutSubscription.objects.all(),
            "ATHLETE@example.test",
        )
        partial_slug, _ = subscription_admin.get_search_results(
            None,
            PublicWorkoutSubscription.objects.all(),
            "bruno-upper",
        )
        partial_email, _ = subscription_admin.get_search_results(
            None,
            PublicWorkoutSubscription.objects.all(),
            "athlete",
        )

    assert list(exact_email.values_list("pk", flat=True)) == [subscription.pk]
    assert list(partial_slug.values_list("pk", flat=True)) == [subscription.pk]
    assert list(partial_email.values_list("pk", flat=True)) == []
    assert other_subscription.pk not in list(exact_email.values_list("pk", flat=True))


def test_coach_roster_keeps_email_alpha_order_without_database_ordering():
    class Row:
        def __init__(self, account_id, email):
            self.account_id = account_id
            self.account = type("Account", (), {"email": email})()

    rows = [Row(3, "zeta@example.test"), Row(2, "Alpha@example.test"), Row(1, "alpha@example.test")]

    assert [row.account_id for row in _sort_coach_roster_rows_by_account_email(rows)] == [1, 2, 3]


@pytest.mark.parametrize(
    ("admin_class", "model"),
    (
        (PublicWorkoutWorkItemAdmin, PublicWorkoutWorkItem),
        (PublicWorkoutNutritionProfileAdmin, PublicWorkoutNutritionProfile),
        (PublicWorkoutMealPlanAdmin, PublicWorkoutMealPlan),
        (PublicWorkoutProgramDraftAdmin, PublicWorkoutProgramDraft),
        (PublicWorkoutRefundRequestAdmin, PublicWorkoutRefundRequest),
        (PublicWorkoutTestimonialAdmin, PublicWorkoutTestimonial),
    ),
)
def test_related_admins_scope_exact_email_search_through_account(admin_class, model):
    key = "account-email-test-key"
    with schema_context(get_public_schema_name()), override_settings(
        EMAIL_BLIND_INDEX_KEY=key,
        PUBLIC_WORKOUT_ACCOUNT_EMAIL_LOOKUP_INDEX_READY=True,
    ):
        account = PublicWorkoutAccount.objects.create(email="in-scope@example.test")
        unrelated_account = PublicWorkoutAccount.objects.create(email="out-of-scope@example.test")
        admin_instance = admin_class(model, admin.site)

        # Empty related model result sets still compile each configured FK path.
        results, use_distinct = admin_instance.get_search_results(
            None,
            model.objects.none(),
            "in-scope@example.test",
        )
        assert list(results) == []
        assert use_distinct is False

        # The account candidates are restricted to the input queryset's account scope.
        scoped_accounts = PublicWorkoutAccount.objects.filter(pk=account.pk)
        matches = public_workout_accounts_for_email(
            "in-scope@example.test",
            queryset=scoped_accounts,
        )
        assert [item.pk for item in matches] == [account.pk]
        assert unrelated_account.pk not in [item.pk for item in matches]


def test_get_or_create_uses_normalized_reader_and_creates_once():
    with schema_context(get_public_schema_name()):
        first, created_first = get_or_create_public_workout_account(
            email="Person@Example.Test", defaults={"photo_url": "https://example.test/avatar"},
        )
        second, created_second = get_or_create_public_workout_account(
            email=" person@example.test ", defaults={"photo_url": "https://example.test/other"},
        )

    assert created_first is True
    assert created_second is False
    assert first.pk == second.pk
    assert second.photo_url == "https://example.test/avatar"


def test_email_index_backfill_dry_run_apply_verify_and_duplicate_report(capsys):
    public_schema = get_public_schema_name()
    with schema_context(public_schema):
        baseline_missing = PublicWorkoutAccount.objects.filter(email_lookup_index="").count()
        lower = PublicWorkoutAccount.objects.create(email="duplicate@example.test")
        upper = PublicWorkoutAccount.objects.create(email="DUPLICATE@example.test")
        field = PublicWorkoutAccount._meta.get_field("email_lookup_index")
        assert field.db_type(connection) == "varchar(67)"

    key = "account-email-test-key"
    with override_settings(EMAIL_BLIND_INDEX_KEY=key):
        call_command("backfill_public_workout_account_email_lookup_index", batch_size=1)
        dry_run = json.loads(capsys.readouterr().out)
        assert dry_run["mode"] == "dry-run"
        assert dry_run["missing_index"] == baseline_missing + 2
        assert dry_run["written"] == 0
        with schema_context(public_schema):
            assert list(PublicWorkoutAccount.objects.filter(
                pk__in=[lower.pk, upper.pk],
            ).values_list("email_lookup_index", flat=True)) == ["", ""]

        call_command("backfill_public_workout_account_email_lookup_index", apply=True, batch_size=1)
        applied = json.loads(capsys.readouterr().out)
        assert applied["written"] == baseline_missing + 2

        call_command("backfill_public_workout_account_email_lookup_index", verify=True, batch_size=1)
        verified = json.loads(capsys.readouterr().out)

    assert verified["mode"] == "verify"
    assert verified["missing_index"] == 0
    assert verified["drift"] == 0
    assert verified["email_duplicate_index_groups"] >= 1
    assert verified["duplicate_scan_complete"] is True
    assert "duplicate@example.test" not in json.dumps([dry_run, applied, verified])
    assert generate_public_workout_account_email_blind_index(
        lower.email, key=key,
    ) == generate_public_workout_account_email_blind_index(upper.email, key=key)
