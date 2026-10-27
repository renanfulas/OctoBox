#!/usr/bin/env python3
"""Create and verify PII-free manifests for OctoBOX PostgreSQL archives."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path


MANIFEST_VERSION = 1
_DB_NAME = re.compile(r'^[a-z][a-z0-9_-]{0,62}$')
_SCHEMA = re.compile(r'^box_[a-z][a-z0-9-]{1,55}$')
_TENANT_METADATA_KEYS = {
    'object_counts',
    'cross_schema_foreign_keys',
    'extensions',
    'grants',
    'schema_grants',
    'latest_django_migrations',
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f'.{path.name}.', suffix='.tmp', dir=path.parent)
    try:
        if hasattr(os, 'fchmod'):
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
        if hasattr(os, 'chmod'):
            os.chmod(path, 0o600)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def _archive_fields(dump_path: Path) -> dict:
    if not dump_path.is_file() or dump_path.stat().st_size <= 0:
        raise ValueError('arquivo de dump ausente ou vazio')
    return {
        'filename': dump_path.name,
        'size_bytes': dump_path.stat().st_size,
        'sha256': sha256_file(dump_path),
    }


def _base_manifest(*, archive_type: str, dump_path: Path, database: str, server_version: str,
                   server_version_num: int, pg_tool_version: str) -> dict:
    if not _DB_NAME.fullmatch(database):
        raise ValueError('nome do banco de origem invalido')
    if server_version_num <= 0:
        raise ValueError('server_version_num invalido')
    return {
        'manifest_version': MANIFEST_VERSION,
        'archive_type': archive_type,
        'source_database': database,
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'postgres_server_version': server_version,
        'postgres_server_version_num': int(server_version_num),
        'postgres_tool_version': pg_tool_version,
        'archive': _archive_fields(dump_path),
    }


def create_full_manifest(*, dump_path: Path, manifest_path: Path, database: str,
                         server_version: str, server_version_num: int,
                         pg_dump_version: str) -> dict:
    value = _base_manifest(
        archive_type='full_database', dump_path=dump_path, database=database,
        server_version=server_version, server_version_num=server_version_num,
        pg_tool_version=pg_dump_version,
    )
    _write_json_atomic(manifest_path, value)
    return value


def create_tenant_manifest(*, dump_path: Path, manifest_path: Path, schema: str,
                           database: str, server_version: str, server_version_num: int,
                           pg_dump_version: str, metadata: dict) -> dict:
    if not _SCHEMA.fullmatch(schema):
        raise ValueError('schema de tenant invalido')
    unexpected_keys = set(metadata) - _TENANT_METADATA_KEYS
    if unexpected_keys:
        raise ValueError(f'metadados de tenant nao permitidos: {sorted(unexpected_keys)}')
    value = _base_manifest(
        archive_type='tenant_schema', dump_path=dump_path, database=database,
        server_version=server_version, server_version_num=server_version_num,
        pg_tool_version=pg_dump_version,
    )
    value['schema'] = schema
    value['metadata'] = metadata
    _write_json_atomic(manifest_path, value)
    return value


def _read_and_verify_manifest(manifest_path: Path, dump_path: Path, expected_type: str) -> dict:
    try:
        value = json.loads(manifest_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f'manifest ausente ou invalido: {manifest_path.name}') from exc
    if value.get('manifest_version') != MANIFEST_VERSION or value.get('archive_type') != expected_type:
        raise ValueError('versao/tipo de manifest incompatível')
    archive = value.get('archive') or {}
    if archive.get('filename') != dump_path.name:
        raise ValueError('manifest pertence a outro arquivo de dump')
    if not dump_path.is_file() or dump_path.stat().st_size != archive.get('size_bytes'):
        raise ValueError('tamanho do dump difere do manifest')
    if sha256_file(dump_path) != archive.get('sha256'):
        raise ValueError('SHA-256 do dump difere do manifest')
    return value


def verify_restore_pair(*, tenant_dump: Path, tenant_manifest_path: Path,
                        base_dump: Path, base_manifest_path: Path,
                        expected_schema: str, target_database: str,
                        target_server_version_num: int, pg_restore_version: str) -> tuple[dict, dict]:
    if not _SCHEMA.fullmatch(expected_schema):
        raise ValueError('schema de tenant invalido')
    if not _DB_NAME.fullmatch(target_database) or not target_database.startswith('octobox_restore_'):
        raise ValueError('o destino deve ser um banco novo com prefixo octobox_restore_')
    tenant = _read_and_verify_manifest(tenant_manifest_path, tenant_dump, 'tenant_schema')
    base = _read_and_verify_manifest(base_manifest_path, base_dump, 'full_database')
    if tenant.get('schema') != expected_schema:
        raise ValueError('slug/schema do pedido nao corresponde ao dump')
    for reference in (tenant.get('metadata') or {}).get('cross_schema_foreign_keys', []):
        if reference.get('direction') == 'shared_to_tenant' or (
            reference.get('target_schema') == expected_schema
            and reference.get('source_schema') != expected_schema
        ):
            raise ValueError('FK entrante de outro schema exige reconciliacao; restore seletivo bloqueado')
    if tenant.get('source_database') != base.get('source_database'):
        raise ValueError('dump tenant e base full vieram de bancos diferentes')
    if target_database == tenant.get('source_database'):
        raise ValueError('o destino coincide com o banco de origem')
    source_major = int(tenant.get('postgres_server_version_num', 0)) // 10000
    base_major = int(base.get('postgres_server_version_num', 0)) // 10000
    target_major = int(target_server_version_num) // 10000
    tool_match = re.search(r'\b(\d+)(?:\.\d+)?\b', pg_restore_version)
    restore_major = int(tool_match.group(1)) if tool_match else 0
    dump_majors = []
    for archive_manifest in (tenant, base):
        dump_match = re.search(r'\b(\d+)(?:\.\d+)?\b', str(archive_manifest.get('postgres_tool_version') or ''))
        dump_majors.append(int(dump_match.group(1)) if dump_match else 0)
    if not source_major or source_major != base_major or source_major != target_major:
        raise ValueError('major do PostgreSQL de origem, base e destino precisa coincidir')
    if not restore_major or min(dump_majors) <= 0 or restore_major < max(dump_majors):
        raise ValueError('pg_restore precisa ter major igual ou superior aos clientes pg_dump dos arquivos')
    return tenant, base


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest='command', required=True)

    for command in ('create-full', 'create-tenant'):
        child = subparsers.add_parser(command)
        child.add_argument('--dump', required=True, type=Path)
        child.add_argument('--manifest', required=True, type=Path)
        child.add_argument('--database', required=True)
        child.add_argument('--server-version', required=True)
        child.add_argument('--server-version-num', required=True, type=int)
        child.add_argument('--pg-dump-version', required=True)
        if command == 'create-tenant':
            child.add_argument('--schema', required=True)
            child.add_argument('--metadata-json', required=True)

    verify = subparsers.add_parser('verify-restore')
    verify.add_argument('--tenant-dump', required=True, type=Path)
    verify.add_argument('--tenant-manifest', required=True, type=Path)
    verify.add_argument('--base-dump', required=True, type=Path)
    verify.add_argument('--base-manifest', required=True, type=Path)
    verify.add_argument('--schema', required=True)
    verify.add_argument('--target-database', required=True)
    verify.add_argument('--target-server-version-num', required=True, type=int)
    verify.add_argument('--pg-restore-version', required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == 'create-full':
            result = create_full_manifest(
                dump_path=args.dump, manifest_path=args.manifest, database=args.database,
                server_version=args.server_version, server_version_num=args.server_version_num,
                pg_dump_version=args.pg_dump_version,
            )
        elif args.command == 'create-tenant':
            metadata = json.loads(args.metadata_json)
            result = create_tenant_manifest(
                dump_path=args.dump, manifest_path=args.manifest, schema=args.schema,
                database=args.database, server_version=args.server_version,
                server_version_num=args.server_version_num, pg_dump_version=args.pg_dump_version,
                metadata=metadata,
            )
        else:
            verify_restore_pair(
                tenant_dump=args.tenant_dump, tenant_manifest_path=args.tenant_manifest,
                base_dump=args.base_dump, base_manifest_path=args.base_manifest,
                expected_schema=args.schema, target_database=args.target_database,
                target_server_version_num=args.target_server_version_num,
                pg_restore_version=args.pg_restore_version,
            )
            print('Manifestos, hashes, origem e versões do destino aprovados.')
            return 0
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise SystemExit(f'erro: {exc}') from exc
    print(f"manifest criado: {args.manifest} ({result['archive']['sha256']})")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
