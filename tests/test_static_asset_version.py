from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from access import context_processors


class StaticAssetVersionTests(SimpleTestCase):
    def setUp(self):
        self._previous_cache = dict(context_processors._ASSET_VERSION_CACHE)
        context_processors._ASSET_VERSION_CACHE.update(
            {'checked_at': 0.0, 'value': '1', 'boot_calculated': False}
        )

    def tearDown(self):
        context_processors._ASSET_VERSION_CACHE.clear()
        context_processors._ASSET_VERSION_CACHE.update(self._previous_cache)

    @override_settings(DEBUG=False, STATIC_ASSET_VERSION='1')
    def test_default_version_uses_asset_mtime_in_production(self):
        with patch.object(context_processors, '_calculate_static_asset_version', return_value='123456') as calculate:
            self.assertEqual(context_processors._build_static_asset_version(), '123456')
            self.assertEqual(context_processors._build_static_asset_version(), '123456')
        calculate.assert_called_once()

    @override_settings(DEBUG=False, STATIC_ASSET_VERSION='release-2026-09-25')
    def test_explicit_release_version_is_kept(self):
        with patch.object(context_processors, '_calculate_static_asset_version') as calculate:
            self.assertEqual(context_processors._build_static_asset_version(), 'release-2026-09-25')
        calculate.assert_not_called()
