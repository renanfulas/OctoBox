import json
from pathlib import Path

import pytest

from scripts.linux.tenant_backup_manifest import (
    create_full_manifest,
    create_tenant_manifest,
    verify_restore_pair,
)


def _archives(tmp_path: Path):
    tenant_dump = tmp_path / 'tenant-box-alpha-20261023-120000.dump'
    tenant_dump.write_bytes(b'tenant archive bytes')
    base_dump = tmp_path / 'octobox-20261023-120000.dump'
    base_dump.write_bytes(b'full archive bytes')
    tenant_manifest = tmp_path / f'{tenant_dump.name}.manifest.json'
    base_manifest = tmp_path / f'{base_dump.name}.manifest.json'
    shared = {
        'database': 'octobox_control',
        'server_version': '15.19',
        'server_version_num': 150019,
        'pg_dump_version': 'pg_dump (PostgreSQL) 15.19',
    }
    create_full_manifest(
        dump_path=base_dump,
        manifest_path=base_manifest,
        database=shared['database'],
        server_version=shared['server_version'],
        server_version_num=shared['server_version_num'],
        pg_dump_version=shared['pg_dump_version'],
    )
    create_tenant_manifest(
        dump_path=tenant_dump,
        manifest_path=tenant_manifest,
        schema='box_alpha',
        database=shared['database'],
        server_version=shared['server_version'],
        server_version_num=shared['server_version_num'],
        pg_dump_version=shared['pg_dump_version'],
        metadata={
            'object_counts': {'tables': 10, 'sequences': 10, 'owned_sequences': 10},
            'cross_schema_foreign_keys': [
                {'direction': 'tenant_to_shared', 'target_schema': 'public', 'target_table': 'auth_user'}
            ],
            'extensions': [{'name': 'plpgsql', 'version': '1.0', 'schema': 'pg_catalog'}],
            'grants': [],
            'schema_grants': [],
            'latest_django_migrations': {'boxcore': '0031_example'},
        },
    )
    return tenant_dump, tenant_manifest, base_dump, base_manifest


def test_tenant_manifest_records_integrity_and_catalog_metadata_without_rows(tmp_path):
    tenant_dump, tenant_manifest, _, _ = _archives(tmp_path)

    manifest = json.loads(tenant_manifest.read_text(encoding='utf-8'))

    assert manifest['archive']['sha256']
    assert manifest['archive']['size_bytes'] == tenant_dump.stat().st_size
    assert manifest['schema'] == 'box_alpha'
    assert manifest['metadata']['cross_schema_foreign_keys'][0]['target_table'] == 'auth_user'
    assert 'rows' not in manifest
    assert 'password' not in manifest


def test_restore_pair_rejects_tampered_dump(tmp_path):
    tenant_dump, tenant_manifest, base_dump, base_manifest = _archives(tmp_path)
    tenant_dump.write_bytes(b'x' * tenant_dump.stat().st_size)

    with pytest.raises(ValueError, match='SHA-256'):
        verify_restore_pair(
            tenant_dump=tenant_dump,
            tenant_manifest_path=tenant_manifest,
            base_dump=base_dump,
            base_manifest_path=base_manifest,
            expected_schema='box_alpha',
            target_database='octobox_restore_run1',
            target_server_version_num=150019,
            pg_restore_version='pg_restore (PostgreSQL) 15.19',
        )


def test_restore_pair_rejects_incoming_foreign_keys_owned_by_a_neighbor(tmp_path):
    tenant_dump, tenant_manifest, base_dump, base_manifest = _archives(tmp_path)
    manifest = json.loads(tenant_manifest.read_text(encoding='utf-8'))
    manifest['metadata']['cross_schema_foreign_keys'].append({
        'direction': 'shared_to_tenant', 'source_schema': 'box_bravo',
        'source_table': 'dependent', 'target_schema': 'box_alpha', 'target_table': 'item',
    })
    tenant_manifest.write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ValueError, match='FK entrante'):
        verify_restore_pair(
            tenant_dump=tenant_dump, tenant_manifest_path=tenant_manifest,
            base_dump=base_dump, base_manifest_path=base_manifest,
            expected_schema='box_alpha', target_database='octobox_restore_review',
            target_server_version_num=150019, pg_restore_version='pg_restore 15.19',
        )


@pytest.mark.parametrize(
    ('target_database', 'schema', 'target_version', 'restore_version', 'message'),
    [
        ('octobox_control', 'box_alpha', 150019, 'pg_restore 15.19', 'prefix'),
        ('octobox_restore_run2', 'box_other', 150019, 'pg_restore 15.19', 'slug/schema'),
        ('octobox_restore_run3', 'box_alpha', 160001, 'pg_restore 15.19', 'major'),
        ('octobox_restore_run4', 'box_alpha', 150019, 'pg_restore 14.0', 'major'),
    ],
)
def test_restore_pair_rejects_unsafe_target_or_version(tmp_path, target_database, schema,
                                                       target_version, restore_version, message):
    tenant_dump, tenant_manifest, base_dump, base_manifest = _archives(tmp_path)

    with pytest.raises(ValueError, match=message):
        verify_restore_pair(
            tenant_dump=tenant_dump,
            tenant_manifest_path=tenant_manifest,
            base_dump=base_dump,
            base_manifest_path=base_manifest,
            expected_schema=schema,
            target_database=target_database,
            target_server_version_num=target_version,
            pg_restore_version=restore_version,
        )
