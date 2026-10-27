"""Key loading primitives for the versioned PII encryption transition.

This module intentionally does not change the existing encrypted model fields.
G2 will connect those fields only after every reader has been deployed.
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from typing import Mapping

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import force_bytes


LEGACY_DJANGO_SECRET_KEY_ID = "legacy-django-secret-v1"
_KEY_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")


class CryptoKeyringError(ValueError):
    """Sanitized key configuration or key selection error."""


@dataclass(frozen=True)
class CryptoKeyring:
    """Validated Fernet keys indexed by non-secret identifiers."""

    keys: Mapping[str, Fernet]
    active_key_id: str | None

    def active(self) -> tuple[str, Fernet]:
        key_id = self.active_key_id
        if not key_id or key_id not in self.keys or key_id == LEGACY_DJANGO_SECRET_KEY_ID:
            raise CryptoKeyringError("PII active encryption key is not configured")
        return key_id, self.keys[key_id]


def derive_legacy_fernet_key(secret_key: str | bytes) -> bytes:
    """Reproduce crypto_fields.py's historical SECRET_KEY derivation exactly."""

    raw_key = force_bytes(secret_key)[:32].ljust(32, b"O")
    return base64.urlsafe_b64encode(raw_key)


def _validated_key(key_id: str, encoded_key: str) -> Fernet:
    if not isinstance(key_id, str) or not _KEY_ID_RE.fullmatch(key_id):
        raise CryptoKeyringError("PII keyring contains an invalid key ID")
    if key_id == LEGACY_DJANGO_SECRET_KEY_ID:
        raise CryptoKeyringError("PII keyring uses a reserved key ID")
    if not isinstance(encoded_key, str):
        raise CryptoKeyringError("PII keyring contains an invalid key")
    try:
        raw_key = encoded_key.encode("ascii")
        decoded = base64.urlsafe_b64decode(raw_key)
        if len(decoded) != 32 or base64.urlsafe_b64encode(decoded) != raw_key:
            raise ValueError
        return Fernet(raw_key)
    except Exception as exc:
        raise CryptoKeyringError("PII keyring contains an invalid key") from exc


def _reject_duplicate_key_ids(pairs):
    """Reject ambiguous JSON objects instead of silently taking the last key."""

    result = {}
    for key_id, encoded_key in pairs:
        if key_id in result:
            raise ValueError("duplicate-key-id")
        result[key_id] = encoded_key
    return result


def load_crypto_keyring(*, keyring_json: str | None = None, active_key_id: str | None = None,
                        secret_key: str | bytes | None = None) -> CryptoKeyring:
    """Parse new data keys and add the exact legacy key for compatible reads.

    The JSON value is an object of ``key_id: Fernet URL-safe base64 key``. Key
    material and parser details are never included in raised messages.
    """

    if keyring_json is None:
        keyring_json = getattr(settings, "PII_ENCRYPTION_KEYRING_JSON", "")
    if active_key_id is None:
        active_key_id = getattr(settings, "PII_ENCRYPTION_ACTIVE_KEY_ID", "")
    if secret_key is None:
        secret_key = settings.SECRET_KEY

    raw_config = keyring_json or "{}"
    try:
        parsed = json.loads(raw_config, object_pairs_hook=_reject_duplicate_key_ids)
    except (TypeError, ValueError) as exc:
        raise CryptoKeyringError("PII keyring configuration is not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise CryptoKeyringError("PII keyring configuration must be a JSON object")

    keys: dict[str, Fernet] = {}
    if secret_key:
        try:
            # Legacy tokens are most common and have no key ID. Put the current
            # derivation first to keep the normal decrypt path O(1).
            keys[LEGACY_DJANGO_SECRET_KEY_ID] = Fernet(derive_legacy_fernet_key(secret_key))
        except Exception as exc:
            raise CryptoKeyringError("Legacy PII reader key is invalid") from exc
    for key_id, encoded_key in parsed.items():
        keys[key_id] = _validated_key(key_id, encoded_key)

    active_key_id = active_key_id or None
    if active_key_id and active_key_id not in keys:
        raise CryptoKeyringError("PII active key ID is not present in the keyring")
    if active_key_id == LEGACY_DJANGO_SECRET_KEY_ID:
        raise CryptoKeyringError("Legacy PII key cannot be selected for new writes")
    return CryptoKeyring(keys=keys, active_key_id=active_key_id)


def validate_crypto_keyring_configuration() -> CryptoKeyring:
    """Fail application startup on malformed key config without exposing values."""

    try:
        return load_crypto_keyring()
    except CryptoKeyringError as exc:
        raise ImproperlyConfigured("PII encryption key configuration is invalid") from exc
