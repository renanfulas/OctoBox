"""Encrypted Django fields and stable blind-index functions.

The field reader understands legacy plaintext, legacy Fernet, and the G1
versioned envelope. Explicit per-field writer gates can keep a field on
plaintext while all readers are upgraded; once enabled, this compatibility
writer uses the exact historical SECRET_KEY derivation. Encryption failures
never fall back to plaintext.
"""

import hashlib
import hmac
import logging

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models
from django.utils.encoding import force_bytes, force_str

from shared_support.crypto_codec import decode
from shared_support.crypto_keyring import derive_legacy_fernet_key

logger = logging.getLogger(__name__)


class EncryptedValueReadError(RuntimeError):
    """A stored encrypted value is unreadable; the exception contains no data."""


class EncryptedValueWriteError(RuntimeError):
    """PII encryption failed; callers must abort the surrounding write."""


try:
    # Keep the old writer format for the reader-first release.
    cipher_suite = Fernet(derive_legacy_fernet_key(settings.SECRET_KEY))
    CRYPTO_KEY = derive_legacy_fernet_key(settings.SECRET_KEY)
except Exception as exc:  # pragma: no cover - exercised through monkeypatch/config tests
    logger.critical("Legacy PII encryption key could not be initialized")
    cipher_suite = None
    CRYPTO_KEY = None


def _prepare_encrypted_value(value):
    if value is None or value == "":
        return value
    text_value = force_str(value)

    # Model instances read plaintext from from_db_value; caller-supplied values
    # are always treated as user data and encrypted, even if they resemble a
    # ciphertext. Raw migration/backfill writes use an explicit lower-level API.
    if cipher_suite is None:
        raise EncryptedValueWriteError("Legacy PII encryption is unavailable")
    try:
        return force_str(cipher_suite.encrypt(force_bytes(text_value)))
    except Exception as exc:
        # Never log the value or exception text: backend exceptions may include
        # the plaintext or ciphertext passed to the cryptographic primitive.
        logger.error("PII encryption failed")
        raise EncryptedValueWriteError("PII encryption failed") from exc


def _read_encrypted_value(value):
    if value is None or value == "":
        return value
    try:
        decoded = decode(force_str(value))
    except Exception as exc:
        raise EncryptedValueReadError("PII key configuration is invalid") from exc
    if decoded.is_readable:
        return decoded.plaintext
    # Status labels are controlled constants and do not contain stored data.
    raise EncryptedValueReadError(f"Stored PII is unreadable ({decoded.status})")


class EncryptedCharField(models.CharField):
    """CharField with authenticated reads and fail-closed encrypted writes.

    ``max_length`` remains the logical/input limit. ``storage_max_length`` is
    an optional physical DB capacity used for encrypted values. A named writer
    setting can keep this field plaintext during a reader-first rollout.
    """

    description = "PII string encrypted with Fernet"

    def __init__(self, *args, storage_max_length=None, writer_enabled_setting=None, **kwargs):
        self.storage_max_length = storage_max_length
        self.writer_enabled_setting = writer_enabled_setting
        if storage_max_length is not None:
            logical_max_length = kwargs.get("max_length")
            if not isinstance(storage_max_length, int) or storage_max_length <= 0:
                raise ValueError("storage_max_length must be a positive integer")
            if logical_max_length is not None and storage_max_length < logical_max_length:
                raise ValueError("storage_max_length cannot be smaller than max_length")
        super().__init__(*args, **kwargs)

    def get_internal_type(self):
        return "CharField"

    def db_type(self, connection):
        if self.storage_max_length is not None:
            data_type = connection.data_types.get("CharField")
            if data_type is None:
                return super().db_type(connection)
            params = self.db_type_parameters(connection)
            params["max_length"] = self.storage_max_length
            if callable(data_type):
                return data_type(params)
            return data_type % params
        return super().db_type(connection)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.storage_max_length is not None:
            kwargs["storage_max_length"] = self.storage_max_length
        if self.writer_enabled_setting is not None:
            kwargs["writer_enabled_setting"] = self.writer_enabled_setting
        return name, path, args, kwargs

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if (
            self.writer_enabled_setting
            and not getattr(settings, self.writer_enabled_setting, False)
        ):
            return value
        return _prepare_encrypted_value(value)

    def from_db_value(self, value, expression, connection):
        return _read_encrypted_value(value)


class EncryptedEmailField(EncryptedCharField, models.EmailField):
    """EmailField that reads both plaintext and ciphertext with optional writer gate."""

    description = "Email encrypted with Fernet and readable as legacy plaintext"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 254)
        super().__init__(*args, **kwargs)


class EncryptedTextField(models.TextField):
    """TextField with authenticated reads and fail-closed encrypted writes."""

    description = "PII text encrypted with Fernet"

    def get_internal_type(self):
        return "TextField"

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return _prepare_encrypted_value(value)

    def from_db_value(self, value, expression, connection):
        return _read_encrypted_value(value)


def generate_blind_index(value, *, key=None):
    """Generate the stable deterministic HMAC used for phone equality lookup."""

    if not value:
        return ""
    if key is None:
        key = getattr(settings, "PHONE_BLIND_INDEX_KEY", "")
    if not key:
        return ""

    # Import local to avoid circular dependency.
    from shared_support.phone_numbers import normalize_phone_number

    normalized = normalize_phone_number(value)
    digest = hmac.new(force_bytes(key), force_bytes(normalized), hashlib.sha256).hexdigest()
    return f"v1:{digest}"


def generate_cpf_blind_index(value, *, key=None):
    """Generate a domain-separated deterministic HMAC for exact CPF lookup."""

    digits = "".join(character for character in force_str(value or "") if character.isdigit())
    if not digits:
        return ""
    if key is None:
        key = getattr(settings, "PHONE_BLIND_INDEX_KEY", "")
    if not key:
        return ""

    # Reuse the stable blind-index root without making a CPF fingerprint
    # correlatable with a phone containing the same digits.
    message = f"octobox:cpf:v1:{digits}"
    digest = hmac.new(force_bytes(key), force_bytes(message), hashlib.sha256).hexdigest()
    return f"v1:{digest}"


def generate_email_blind_index(value, *, key=None):
    """Generate a domain-separated HMAC for normalized email equality lookup."""

    return _generate_scoped_email_blind_index(
        value,
        domain="student-identity-email",
        key=key,
    )


def generate_public_workout_account_email_blind_index(value, *, key=None):
    """Generate the independent HMAC used by public workout account lookup."""

    return _generate_scoped_email_blind_index(
        value,
        domain="public-workout-account-email",
        key=key,
    )


def generate_public_workout_checkout_lead_email_blind_index(value, *, key=None):
    """Generate the independent HMAC for unpaid checkout lead lookup."""

    return _generate_scoped_email_blind_index(
        value,
        domain="public-workout-checkout-lead-email",
        key=key,
    )


def generate_public_workout_waitlist_email_blind_index(value, *, key=None):
    """Generate the independent HMAC for public workout waitlist lookup."""

    return _generate_scoped_email_blind_index(
        value,
        domain="public-workout-waitlist-email",
        key=key,
    )


def generate_student_app_invitation_email_blind_index(value, *, key=None):
    """Generate the independent HMAC used for exact invitation email search."""

    return _generate_scoped_email_blind_index(
        value,
        domain="student-app-invitation-email",
        key=key,
    )


def generate_pending_signup_email_blind_index(value, *, key=None):
    """Generate the independent HMAC used for exact PendingSignup email search."""

    return _generate_scoped_email_blind_index(
        value,
        domain="pending-signup-email",
        key=key,
    )


def _generate_scoped_email_blind_index(value, *, domain, key=None):
    """Generate a versioned, purpose-separated HMAC for email equality."""

    normalized = force_str(value or "").strip().casefold()
    if not normalized:
        return ""
    if key is None:
        key = getattr(settings, "EMAIL_BLIND_INDEX_KEY", "")
    if not key:
        return ""

    message = f"octobox:{domain}:v1:{normalized}"
    digest = hmac.new(force_bytes(key), force_bytes(message), hashlib.sha256).hexdigest()
    return f"v1:{digest}"
