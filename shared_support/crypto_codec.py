"""Versioned authenticated envelope codec, not yet wired to model fields."""

from __future__ import annotations

from dataclasses import dataclass

from cryptography.fernet import InvalidToken
from django.utils.encoding import force_bytes, force_str

from shared_support.crypto_keyring import CryptoKeyring, CryptoKeyringError, load_crypto_keyring


ENVELOPE_PREFIX = "octobox:v1:"
_FERNET_PREFIX = "gAAAAA"


@dataclass(frozen=True)
class DecodedValue:
    """Classification and value; ``plaintext`` exists only for valid data."""

    status: str
    plaintext: str | None = None
    key_id: str | None = None

    @property
    def is_readable(self) -> bool:
        return self.status in {"empty", "legacy_plaintext", "legacy_fernet", "envelope"}


def encode(value: str, *, keyring: CryptoKeyring | None = None) -> str:
    """Encrypt with the explicitly active data key; fail closed if absent."""

    if keyring is None:
        keyring = load_crypto_keyring()
    key_id, key = keyring.active()
    token = force_str(key.encrypt(force_bytes(value)))
    return f"{ENVELOPE_PREFIX}{key_id}:{token}"


def decode(value: str | None, *, keyring: CryptoKeyring | None = None) -> DecodedValue:
    """Classify empty, plaintext legacy, Fernet legacy, and versioned values.

    Invalid ciphertext, malformed envelopes, unsupported versions, and unknown
    key IDs are distinct non-readable states. Ciphertext is never returned as a
    plaintext fallback.
    """

    if value is None or value == "":
        return DecodedValue("empty", plaintext=value)
    if keyring is None:
        keyring = load_crypto_keyring()

    if value.startswith("octobox:"):
        parts = value.split(":", 3)
        if len(parts) != 4 or parts[0] != "octobox" or not parts[2] or not parts[3]:
            return DecodedValue("malformed_envelope")
        _, version, key_id, token = parts
        if version != "v1":
            return DecodedValue("unsupported_envelope")
        key = keyring.keys.get(key_id)
        if key is None:
            return DecodedValue("unknown_key", key_id=key_id)
        try:
            plaintext = force_str(key.decrypt(force_bytes(token)))
        except (InvalidToken, ValueError, TypeError):
            return DecodedValue("invalid_ciphertext", key_id=key_id)
        return DecodedValue("envelope", plaintext=plaintext, key_id=key_id)

    if value.startswith(_FERNET_PREFIX):
        # Legacy tokens have no key ID. Try the current exact derivation and
        # explicitly retained historical keys; do not expose attempted keys.
        for key_id, key in keyring.keys.items():
            try:
                plaintext = force_str(key.decrypt(force_bytes(value)))
            except (InvalidToken, ValueError, TypeError):
                continue
            return DecodedValue("legacy_fernet", plaintext=plaintext, key_id=key_id)
        return DecodedValue("invalid_ciphertext")

    return DecodedValue("legacy_plaintext", plaintext=value)


def max_envelope_length(max_plaintext_characters: int, key_id: str) -> int:
    """Worst-case ASCII envelope length for UTF-8 text and Fernet padding."""

    if max_plaintext_characters < 0 or not key_id:
        raise ValueError("A non-negative limit and key ID are required")
    plaintext_bytes = max_plaintext_characters * 4
    padded_ciphertext_bytes = (plaintext_bytes // 16 + 1) * 16
    token_bytes = 4 * ((57 + padded_ciphertext_bytes + 2) // 3)
    return len(ENVELOPE_PREFIX) + len(key_id) + 1 + token_bytes


__all__ = ["DecodedValue", "CryptoKeyringError", "decode", "encode", "max_envelope_length"]
