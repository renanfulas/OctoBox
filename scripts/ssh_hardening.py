import hashlib
import os
from typing import Final

import paramiko


_FINGERPRINT_ENV_NAMES: Final[tuple[str, ...]] = (
    'OCTOBOX_VPS_HOST_FINGERPRINT',
    'OCTOBOX_VPS_HOSTKEY_SHA256',
)


def _normalize_fingerprint(value: str) -> str:
    normalized = (value or '').strip()
    normalized = normalized.removeprefix('SHA256:')
    normalized = normalized.replace(':', '').replace(' ', '')
    return normalized.lower()


def _load_expected_fingerprint() -> str:
    for env_name in _FINGERPRINT_ENV_NAMES:
        raw_value = os.environ.get(env_name, '')
        normalized = _normalize_fingerprint(raw_value)
        if normalized:
            return normalized
    raise RuntimeError(
        'Defina OCTOBOX_VPS_HOST_FINGERPRINT com o fingerprint SHA256 do host antes de usar SSH remoto.'
    )


def _build_host_key_fingerprint(host_key: paramiko.PKey) -> str:
    return hashlib.sha256(host_key.asbytes()).hexdigest()


class RequiredHostKeyPolicy(paramiko.MissingHostKeyPolicy):
    def __init__(self, expected_fingerprint: str):
        self.expected_fingerprint = _normalize_fingerprint(expected_fingerprint)

    def missing_host_key(self, client, hostname, key):
        received_fingerprint = _build_host_key_fingerprint(key)
        if received_fingerprint != self.expected_fingerprint:
            raise paramiko.SSHException(
                f'Fingerprint inesperado para {hostname}. '
                f'Esperado={self.expected_fingerprint} recebido={received_fingerprint}'
            )
        client.get_host_keys().add(hostname, key.get_name(), key)


def build_hardened_ssh_client() -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(
        RequiredHostKeyPolicy(_load_expected_fingerprint())
    )
    return client


__all__ = ['build_hardened_ssh_client']
