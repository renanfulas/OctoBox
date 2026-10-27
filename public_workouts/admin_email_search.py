"""Exact-email search adapters for Django Admin during blind-index rollout."""

from public_workouts.account_email_lookup import public_workout_accounts_for_email


class PublicWorkoutAccountExactEmailSearchMixin:
    account_email_relation = 'account'
    account_email_search_only = False

    def get_search_results(self, request, queryset, search_term):
        if not search_term:
            return queryset, False
        if self.account_email_search_only:
            text_results, use_distinct = queryset.none(), False
        else:
            text_results, use_distinct = super().get_search_results(request, queryset, search_term)
        if '@' not in search_term:
            return text_results, use_distinct
        from public_workouts.models import PublicWorkoutAccount

        account_path = f'{self.account_email_relation}__pk'
        scoped_accounts = queryset.order_by().values(account_path)
        accounts = public_workout_accounts_for_email(
            search_term,
            queryset=PublicWorkoutAccount.objects.filter(pk__in=scoped_accounts),
        )
        relation_id = f'{self.account_email_relation}_id__in'
        email_results = queryset.filter(**{relation_id: [account.pk for account in accounts]})
        return text_results | email_results, use_distinct


class PublicWorkoutCommerceExactEmailSearchMixin:
    email_lookup = None

    def get_search_results(self, request, queryset, search_term):
        if not search_term or '@' not in search_term:
            return queryset.none(), False
        matches = self.email_lookup(search_term, queryset=queryset)
        return queryset.filter(pk__in=[row.pk for row in matches]), False
