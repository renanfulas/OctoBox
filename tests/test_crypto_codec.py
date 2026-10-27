import base64
import json
from unittest.mock import patch

import pytest
import shared_support
from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.test import override_settings

from shared_support.crypto_codec import decode, encode, max_envelope_length
from shared_support.apps import SharedSupportConfig
from shared_support.crypto_keyring import (
    CryptoKeyringError,
    LEGACY_DJANGO_SECRET_KEY_ID,
    derive_legacy_fernet_key,
    load_crypto_keyring,
    validate_crypto_keyring_configuration,
)
from shared_support.crypto_fields import (
    EncryptedCharField,
    EncryptedTextField,
    EncryptedValueReadError,
    EncryptedValueWriteError,
    generate_blind_index,
    generate_cpf_blind_index,
)
from shared_support.management.commands.report_pii_encryption_formats import summarize_raw_values


def test_legacy_key_derivation_matches_historical_field_expression():
    secret = "0123456789abcdef0123456789abcdef-and-more"
    expected = base64.urlsafe_b64encode(secret.encode("utf-8")[:32].ljust(32, b"O"))
    assert derive_legacy_fernet_key(secret) == expected
    assert derive_legacy_fernet_key("short") == derive_legacy_fernet_key(b"short")


def test_codec_round_trips_with_an_explicit_active_data_key():
    key = Fernet.generate_key().decode("ascii")
    keyring = load_crypto_keyring(
        keyring_json=json.dumps({"data-2026-10": key}),
        active_key_id="data-2026-10",
        secret_key="legacy-secret",
    )
    encrypted = encode("PII with unicode: ação 🏋️", keyring=keyring)
    result = decode(encrypted, keyring=keyring)
    assert encrypted.startswith("octobox:v1:data-2026-10:")
    assert result.status == "envelope"
    assert result.plaintext == "PII with unicode: ação 🏋️"
    assert result.key_id == "data-2026-10"


def test_codec_reads_exact_legacy_fernet_derivation():
    legacy_key = derive_legacy_fernet_key("old-django-secret")
    token = Fernet(legacy_key).encrypt(b"legacy value").decode("ascii")
    keyring = load_crypto_keyring(secret_key="old-django-secret")
    result = decode(token, keyring=keyring)
    assert result.status == "legacy_fernet"
    assert result.plaintext == "legacy value"
    assert result.key_id == LEGACY_DJANGO_SECRET_KEY_ID


def test_codec_can_read_a_retained_historical_legacy_key():
    old_key = derive_legacy_fernet_key("old-secret-no-longer-current").decode("ascii")
    token = Fernet(old_key.encode("ascii")).encrypt(b"retained legacy value").decode("ascii")
    keyring = load_crypto_keyring(
        keyring_json=json.dumps({"legacy-2025": old_key}),
        secret_key="new-current-secret",
    )
    result = decode(token, keyring=keyring)
    assert result.status == "legacy_fernet"
    assert result.plaintext == "retained legacy value"
    assert result.key_id == "legacy-2025"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "empty"),
        ("", "empty"),
        ("old plaintext", "legacy_plaintext"),
        ("gAAAAA-not-a-valid-token", "invalid_ciphertext"),
        ("octobox:v1:missing-key:token", "unknown_key"),
        ("octobox:v2:data-key:token", "unsupported_envelope"),
        ("octobox:v1:data-key", "malformed_envelope"),
    ],
)
def test_decode_classifies_legacy_and_invalid_values_without_returning_ciphertext(value, expected):
    keyring = load_crypto_keyring(secret_key="legacy-secret")
    result = decode(value, keyring=keyring)
    assert result.status == expected
    if expected not in {"empty", "legacy_plaintext"}:
        assert result.plaintext is None


def test_new_writer_fails_closed_without_active_key():
    keyring = load_crypto_keyring(secret_key="legacy-secret")
    with pytest.raises(CryptoKeyringError, match="active encryption key"):
        encode("must not become plaintext", keyring=keyring)


def test_boot_validation_accepts_reader_first_empty_keyring():
    with override_settings(PII_ENCRYPTION_KEYRING_JSON='', PII_ENCRYPTION_ACTIVE_KEY_ID=''):
        keyring = validate_crypto_keyring_configuration()
    assert keyring.active_key_id is None
    assert LEGACY_DJANGO_SECRET_KEY_ID in keyring.keys


def test_django_app_startup_hook_rejects_invalid_keyring():
    app_config = SharedSupportConfig('shared_support', shared_support)
    with override_settings(PII_ENCRYPTION_KEYRING_JSON='{invalid'):
        with pytest.raises(ImproperlyConfigured, match='PII encryption key configuration is invalid'):
            app_config.ready()


@pytest.mark.parametrize(
    ('keyring_json', 'active_key_id'),
    [('{invalid', ''), ('{}', 'missing-key')],
)
def test_boot_validation_rejects_invalid_or_missing_active_key_without_secret_details(
    keyring_json, active_key_id,
):
    with override_settings(
        PII_ENCRYPTION_KEYRING_JSON=keyring_json,
        PII_ENCRYPTION_ACTIVE_KEY_ID=active_key_id,
    ):
        with pytest.raises(ImproperlyConfigured, match='PII encryption key configuration is invalid') as exc_info:
            validate_crypto_keyring_configuration()
    assert 'missing-key' not in str(exc_info.value)
    assert '{invalid' not in str(exc_info.value)


@pytest.mark.parametrize(
    ("keyring_json", "active_key_id"),
    [
        ('{"Bad ID":"not a key"}', "Bad ID"),
        ("{", "good-key"),
        ('{"good-key":"not a Fernet key"}', "good-key"),
        ('{"good-key":"u1gIsNX47xEJOAY0AzpQIMvcPUNwSQiatVJHGyM9u6k="}', "missing-key"),
    ],
)
def test_keyring_rejects_bad_configuration_without_echoing_key_material(keyring_json, active_key_id):
    with pytest.raises(CryptoKeyringError):
        load_crypto_keyring(keyring_json=keyring_json, active_key_id=active_key_id, secret_key="legacy")


@pytest.mark.parametrize(
    "keyring_json",
    [
        '{"data-key":"first","data-key":"second"}',
        '{"data-key":"same","data-key":"same"}',
    ],
)
def test_keyring_rejects_duplicate_key_ids_without_echoing_values(keyring_json):
    with pytest.raises(CryptoKeyringError, match="not valid JSON") as exc_info:
        load_crypto_keyring(keyring_json=keyring_json, secret_key="legacy")
    assert "first" not in str(exc_info.value)
    assert "second" not in str(exc_info.value)


def test_worst_case_255_unicode_characters_fit_in_2048_character_storage():
    assert max_envelope_length(255, "k" * 32) == 1488
    assert max_envelope_length(255, "k" * 32) < 2048


def test_encrypted_char_field_keeps_logical_length_and_uses_wider_db_storage():
    field = EncryptedCharField(max_length=255, storage_max_length=2048)
    assert field.max_length == 255
    assert field.db_type(connection) == "varchar(2048)"
    _, _, _, kwargs = field.deconstruct()
    assert kwargs["max_length"] == 255
    assert kwargs["storage_max_length"] == 2048


@pytest.mark.parametrize("field_class", [EncryptedCharField, EncryptedTextField])
def test_fields_write_legacy_format_and_round_trip_plaintext(field_class):
    field = field_class(max_length=255) if field_class is EncryptedCharField else field_class()
    value = "PII round trip"
    stored = field.get_prep_value(value)
    assert stored.startswith("gAAAAA")
    assert field.from_db_value(stored, None, connection) == value


def test_field_reads_authenticated_new_envelope():
    data_key = Fernet.generate_key().decode("ascii")
    keyring_json = json.dumps({"data-2026-10": data_key})
    with override_settings(
        PII_ENCRYPTION_KEYRING_JSON=keyring_json,
        PII_ENCRYPTION_ACTIVE_KEY_ID="data-2026-10",
    ):
        keyring = load_crypto_keyring()
        envelope = encode("new envelope value", keyring=keyring)
        assert EncryptedCharField().from_db_value(envelope, None, connection) == "new envelope value"


def test_field_rejects_invalid_ciphertext_without_exposing_it():
    token = "gAAAAA-invalid-ciphertext"
    with pytest.raises(EncryptedValueReadError) as exc_info:
        EncryptedCharField().from_db_value(token, None, connection)
    assert token not in str(exc_info.value)
    assert "invalid_ciphertext" in str(exc_info.value)


def test_field_encrypts_user_text_that_looks_like_a_fernet_token():
    value = "gAAAAA-user-supplied-text"
    field = EncryptedCharField()
    stored = field.get_prep_value(value)
    assert stored != value
    assert field.from_db_value(stored, None, connection) == value


def test_field_write_fails_closed_when_legacy_encryption_is_unavailable():
    value = "must never persist in plaintext"
    with patch("shared_support.crypto_fields.cipher_suite", None):
        with pytest.raises(EncryptedValueWriteError) as exc_info:
            EncryptedTextField().get_prep_value(value)
    assert value not in str(exc_info.value)


def test_cpf_blind_index_normalizes_format_and_is_domain_separated_from_phone():
    cpf_index = generate_cpf_blind_index("052.484.340-68", key="stable-root")
    same_cpf_index = generate_cpf_blind_index("05248434068", key="stable-root")
    phone_index = generate_blind_index("05248434068", key="stable-root")

    assert cpf_index.startswith("v1:")
    assert cpf_index == same_cpf_index
    assert cpf_index != phone_index
    assert generate_cpf_blind_index("...", key="stable-root") == ""


def test_format_census_returns_aggregates_without_values():
    plaintext = "sensitive-plain-value-5511999999999"
    legacy_token = Fernet(derive_legacy_fernet_key("legacy-secret")).encrypt(
        b"sensitive-encrypted-value-5511888888888"
    ).decode("ascii")
    invalid_token = "gAAAAA-sensitive-invalid-token-5511777777777"
    keyring = load_crypto_keyring(secret_key="legacy-secret")
    aggregate = summarize_raw_values(
        [plaintext, legacy_token, invalid_token, None],
        keyring=keyring,
        logical_limit=255,
    )
    serialized = json.dumps(aggregate)
    assert aggregate["rows"] == 4
    assert aggregate["format_counts"] == {
        "empty": 1,
        "invalid_ciphertext": 1,
        "legacy_fernet": 1,
        "legacy_plaintext": 1,
    }
    assert plaintext not in serialized
    assert legacy_token not in serialized
    assert "5511888888888" not in serialized
    assert "5511777777777" not in serialized


def test_format_census_marks_unencrypted_email_without_emitting_it():
    email = "private-address-5511999999999@example.test"
    keyring = load_crypto_keyring(secret_key="legacy-secret")
    aggregate = summarize_raw_values(
        [email, ""],
        keyring=keyring,
        logical_limit=254,
        plaintext_field=True,
    )
    assert aggregate["format_counts"] == {"empty": 1, "unencrypted_plaintext": 1}
    assert email not in json.dumps(aggregate)
