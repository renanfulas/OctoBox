"""Versão dos assets por deploy (pilar 6 de docs/plans/curva-offline-first-estrategia.md)."""

from django.test import SimpleTestCase

from config.asset_version import static_asset_version


class StaticAssetVersionResolutionTests(SimpleTestCase):
    def test_explicit_value_wins(self):
        self.assertEqual(
            static_asset_version({'STATIC_ASSET_VERSION': 'release-2026-11', 'OCTOBOX_RELEASE_SHA': 'abc'}),
            'release-2026-11',
        )

    def test_release_sha_from_the_vps_deploy_changes_every_deploy(self):
        self.assertEqual(
            static_asset_version({'OCTOBOX_RELEASE_SHA': 'DACA6DA3F00D1234567890ABCDEF'}), 'daca6da3f00d',
        )

    def test_legacy_render_commit_still_works(self):
        self.assertEqual(static_asset_version({'RENDER_GIT_COMMIT': '0123456789abcdef'}), '0123456789ab')

    def test_empty_values_fall_back_to_unconfigured(self):
        # wsgi.py faz setdefault('OCTOBOX_RELEASE_SHA', '') — vazio não é versão.
        self.assertEqual(static_asset_version({'OCTOBOX_RELEASE_SHA': '', 'STATIC_ASSET_VERSION': '  '}), '1')
        self.assertEqual(static_asset_version({}), '1')
