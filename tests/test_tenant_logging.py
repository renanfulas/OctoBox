from types import SimpleNamespace

from django.test import TestCase, override_settings

from shared_support.tenant_logging import tenant_log_ref


class TenantLogRefTests(TestCase):
    @override_settings(SECRET_KEY='tenant-log-ref-test-key')
    def test_reference_is_stable_and_does_not_include_tenant_identifier(self):
        schema = 'box-private-studio'

        first = tenant_log_ref(schema)
        second = tenant_log_ref(schema)

        self.assertEqual(first, second)
        self.assertTrue(first.startswith('tenant:'))
        self.assertNotIn(schema, first)

    @override_settings(SECRET_KEY='tenant-log-ref-test-key')
    def test_box_primary_key_is_the_canonical_reference_material(self):
        first = tenant_log_ref(SimpleNamespace(pk=42, schema_name='box-before-rename'))
        after_schema_rename = tenant_log_ref(SimpleNamespace(pk=42, schema_name='archived_box-after-rename'))

        self.assertEqual(first, after_schema_rename)

    @override_settings(SECRET_KEY='')
    def test_missing_secret_fails_closed_without_echoing_identifier(self):
        self.assertEqual(tenant_log_ref('box-private-studio'), 'tenant:unavailable')
        self.assertEqual(tenant_log_ref(''), 'tenant:unknown')
