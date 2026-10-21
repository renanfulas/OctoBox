"""Regressão: o audit log do Django Admin acompanha o ContentType do tenant."""

import uuid

import pytest
from django.contrib.admin.models import ADDITION, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django_tenants.utils import get_public_schema_name, schema_context

from boxcore.models import Student


@pytest.mark.django_db(transaction=True)
def test_tenant_admin_log_uses_tenant_content_type_and_table(test_tenant):
    with schema_context(get_public_schema_name()):
        user = get_user_model().objects.create_user(
            username=f'tenant-admin-log-{uuid.uuid4().hex}',
        )

    entry_id = None
    try:
        with schema_context(test_tenant.schema_name):
            tables = set(connection.introspection.table_names())
            assert 'django_admin_log' in tables

            content_type = ContentType.objects.get_for_model(Student)
            entry = LogEntry.objects.log_actions(
                user_id=user.pk,
                queryset=[Student(full_name='Aluno auditado')],
                action_flag=ADDITION,
                change_message='Teste de isolamento do audit log.',
                single_object=True,
            )

            assert entry.content_type_id == content_type.pk
            assert LogEntry.objects.filter(pk=entry.pk).exists()
            entry_id = entry.pk
    finally:
        if entry_id is not None:
            with schema_context(test_tenant.schema_name):
                LogEntry.objects.filter(pk=entry_id).delete()
        with schema_context(get_public_schema_name()):
            get_user_model().objects.filter(pk=user.pk).delete()
