from pathlib import Path

import pytest
from django.db import connection, transaction


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('dependency', ('foreign_key', 'view', 'materialized_view'))
def test_restore_preflight_detects_objects_that_cascade_would_remove_from_neighbor(dependency):
    """Execute the same catalog query used by the restore script on PostgreSQL."""
    source = (Path(__file__).resolve().parents[1] / 'scripts/linux/tenant_restore_external_dependencies.sql').read_text(encoding='utf-8')
    parameters = ['box_restore_guard_a'] * source.count(":'tenant_schema'")
    query = source.replace(":'tenant_schema'", '%s')
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute('CREATE SCHEMA box_restore_guard_a; CREATE SCHEMA box_restore_guard_b;')
        cursor.execute('CREATE TABLE box_restore_guard_a.item(id integer PRIMARY KEY);')
        cursor.execute(query, parameters)
        assert cursor.fetchone()[0] == 0
        if dependency == 'foreign_key':
            cursor.execute('CREATE TABLE box_restore_guard_b.item(id integer REFERENCES box_restore_guard_a.item(id));')
        elif dependency == 'view':
            cursor.execute('CREATE VIEW box_restore_guard_b.items AS SELECT * FROM box_restore_guard_a.item;')
        else:
            cursor.execute('CREATE MATERIALIZED VIEW box_restore_guard_b.items AS SELECT * FROM box_restore_guard_a.item;')
        cursor.execute(query, parameters)
        assert cursor.fetchone()[0] > 0
        # All objects belong to this disposable test transaction.
        transaction.set_rollback(True)
