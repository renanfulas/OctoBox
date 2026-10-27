"""Admin search helpers for values stored in randomized encrypted fields."""

import re

from shared_support.crypto_fields import generate_blind_index
from shared_support.phone_numbers import normalize_phone_number


_PHONE_SEARCH_INPUT = re.compile(r"^[+0-9().\-\s]+$")


class BlindIndexPhoneSearchAdminMixin:
    """Add exact phone search through a model's deterministic blind index.

    Django's default ``icontains`` lookup cannot search Fernet ciphertext. Keep
    ``search_fields`` limited to plaintext fields and set ``phone_lookup_path``
    to the blind-index field path (including relations where needed).
    """

    phone_lookup_path = "phone_lookup_index"

    def get_search_results(self, request, queryset, search_term):
        base_queryset = queryset
        search_queryset, may_have_duplicates = super().get_search_results(
            request,
            queryset,
            search_term,
        )

        raw_term = str(search_term or "").strip()
        if not raw_term or not _PHONE_SEARCH_INPUT.fullmatch(raw_term):
            return search_queryset, may_have_duplicates

        normalized = normalize_phone_number(raw_term)
        if not 8 <= len(normalized) <= 15:
            return search_queryset, may_have_duplicates

        phone_index = generate_blind_index(raw_term)
        if not phone_index:
            return search_queryset, may_have_duplicates

        exact_phone_matches = base_queryset.filter(**{self.phone_lookup_path: phone_index})
        return search_queryset | exact_phone_matches, may_have_duplicates


__all__ = ["BlindIndexPhoneSearchAdminMixin"]
