"""
ARQUIVO: testes do contrato compartilhado de page payloads.

POR QUE ELE EXISTE:
- protege a regra de heroes curtos e previsiveis nas superficies principais.

O QUE ESTE ARQUIVO FAZ:
1. valida que o builder de hero limita acoes principais.
2. protege a regra minima para evitar que o bloco volte a crescer sem controle.
"""

from django.test import SimpleTestCase

from shared_support.page_payloads import PAGE_HERO_CONTENT_RULES, attach_page_payload, build_page_assets, build_page_hero, build_page_payload
from shared_support.static_assets import clear_runtime_css_cache, resolve_runtime_css_paths, sync_static_to_staticfiles
from shared_support.surface_runtime_contracts import build_asset_behavior, build_surface_behavior, build_surface_runtime_contract


class PageHeroContractTests(SimpleTestCase):
    def test_build_page_hero_enforces_shared_minimal_contract(self):
        hero = build_page_hero(
            eyebrow='Teste',
            title='Hero enxuto',
            copy='Uma frase curta para manter leitura direta.',
            actions=[
                {'label': 'Acao 1', 'href': '#1'},
                {'label': 'Acao 2', 'href': '#2'},
                {'label': 'Acao 3', 'href': '#3'},
                {'label': 'Acao 4', 'href': '#4'},
            ],
        )

        self.assertEqual(hero['contract'], PAGE_HERO_CONTENT_RULES)
        self.assertEqual(len(hero['actions']), PAGE_HERO_CONTENT_RULES['max_primary_actions'])
        self.assertEqual(hero['contract']['max_title_lines'], 2)
        self.assertEqual(hero['contract']['max_copy_lines'], 2)

    def test_build_page_hero_allows_local_override_for_primary_actions(self):
        hero = build_page_hero(
            eyebrow='Teste',
            title='Hero com excecao controlada',
            copy='Uma frase curta para manter leitura direta.',
            actions=[
                {'label': 'Acao 1', 'href': '#1'},
                {'label': 'Acao 2', 'href': '#2'},
                {'label': 'Acao 3', 'href': '#3'},
                {'label': 'Acao 4', 'href': '#4'},
            ],
            contract={'max_primary_actions': 4},
        )

        self.assertEqual(len(hero['actions']), 4)
        self.assertEqual(hero['contract']['max_primary_actions'], 4)
        self.assertEqual(hero['contract']['max_title_lines'], 2)
        self.assertEqual(hero['contract']['max_copy_lines'], 2)


class PagePayloadBridgeContractTests(SimpleTestCase):
    def test_attach_page_payload_propagates_shared_contract_to_page_context(self):
        context = {
            'current_page_assets': {
                'css': ['css/shared/base.css'],
                'js': ['js/shared/base.js'],
            }
        }
        payload = build_page_payload(
            context={
                'page_key': 'students',
                'title': 'Alunos',
                'subtitle': 'Leitura cruzada da base.',
            },
            behavior={
                'workspace_storage_key': 'octobox-students-layout-v1',
            },
            assets=build_page_assets(
                css=['css/catalog/students.css', 'css/shared/base.css'],
                js=['js/pages/student-form.js'],
            ),
        )

        result = attach_page_payload(context, payload_key='student_directory_page', payload=payload)

        self.assertIn('student_directory_page', result)
        self.assertEqual(result['page_title'], 'Alunos')
        self.assertEqual(result['page_subtitle'], 'Leitura cruzada da base.')
        self.assertEqual(result['current_page_behavior'], payload['behavior'])
        self.assertEqual(
            result['current_page_assets']['css'],
            ['css/shared/base.css', 'css/catalog/students.css'],
        )
        self.assertEqual(
            result['current_page_assets']['js'],
            ['js/shared/base.js', 'js/pages/student-form.js'],
        )
        self.assertEqual(
            result['current_page_assets']['css_runtime'],
            resolve_runtime_css_paths(['css/shared/base.css', 'css/catalog/students.css']),
        )
        self.assertTrue(result['current_page_assets']['has_runtime_css_groups'])
        self.assertEqual(result['page_assets'], result['current_page_assets'])

    def test_attach_page_payload_tracks_priority_asset_groups(self):
        context = {
            'current_page_assets': {
                'css': ['css/shared/base.css'],
                'js': ['js/shared/base.js'],
                'critical_css': ['css/design-system/tokens.css'],
                'deferred_css': ['css/design-system/topbar.css'],
                'enhancement_css': [],
                'critical_js': ['js/core/base.js'],
                'deferred_js': [],
            }
        }
        payload = build_page_payload(
            context={
                'page_key': 'students',
                'title': 'Alunos',
            },
            assets=build_page_assets(
                css=['css/catalog/students.css'],
                js=['js/pages/student-form.js'],
                critical_css=['css/design-system/components/hero.css'],
                deferred_css=['css/design-system/sidebar/base.css'],
                enhancement_css=['css/design-system/neon.css'],
                critical_js=['js/core/page-critical.js'],
                deferred_js=['js/pages/page-deferred.js'],
            ),
        )

        result = attach_page_payload(context, payload_key='student_directory_page', payload=payload)
        current_page_assets = result['current_page_assets']

        self.assertEqual(
            current_page_assets['critical_css'],
            ['css/design-system/tokens.css', 'css/design-system/components/hero.css'],
        )
        self.assertEqual(
            current_page_assets['deferred_css'],
            ['css/design-system/topbar.css', 'css/design-system/sidebar/base.css'],
        )
        self.assertEqual(
            current_page_assets['enhancement_css'],
            ['css/design-system/neon.css'],
        )
        self.assertEqual(
            current_page_assets['critical_js'],
            ['js/core/base.js', 'js/core/page-critical.js'],
        )
        self.assertEqual(
            current_page_assets['deferred_js'],
            ['js/pages/page-deferred.js'],
        )
        self.assertEqual(
            current_page_assets['critical_css_runtime'],
            resolve_runtime_css_paths(['css/design-system/tokens.css', 'css/design-system/components/hero.css']),
        )
        self.assertEqual(
            current_page_assets['deferred_css_runtime'],
            resolve_runtime_css_paths(['css/design-system/topbar.css', 'css/design-system/sidebar/base.css']),
        )
        self.assertEqual(
            current_page_assets['enhancement_css_runtime'],
            resolve_runtime_css_paths(['css/design-system/neon.css']),
        )

    def test_attach_page_payload_dedupes_rendered_css_between_priority_groups(self):
        payload = build_page_payload(
            context={
                'page_key': 'students',
                'title': 'Alunos',
            },
            assets=build_page_assets(
                critical_css=['css/design-system/tokens.css'],
                css=['css/design-system.css'],
            ),
        )

        result = attach_page_payload({}, payload_key='student_directory_page', payload=payload)
        current_page_assets = result['current_page_assets']

        self.assertIn('css/design-system/tokens.css', current_page_assets['critical_css_runtime'])
        self.assertNotIn('css/design-system/tokens.css', current_page_assets['css_runtime'])

    def test_resolve_runtime_css_paths_expands_manifest_imports(self):
        resolved = resolve_runtime_css_paths(['css/design-system.css'])

        self.assertIn('css/design-system/tokens.css', resolved)
        self.assertIn('css/design-system/components/hero.css', resolved)
        self.assertNotIn('css/design-system.css', resolved)

    def test_resolve_runtime_css_paths_preserves_bundled_manifest(self):
        resolved = resolve_runtime_css_paths(['bundle:css/catalog/students-deferred.css'])

        self.assertEqual(resolved, ['css/catalog/students-deferred.css'])

    def test_clear_runtime_css_cache_allows_recompute(self):
        first = resolve_runtime_css_paths(['css/design-system.css'])
        clear_runtime_css_cache()
        second = resolve_runtime_css_paths(['css/design-system.css'])

        self.assertEqual(first, second)

    def test_sync_static_to_staticfiles_copies_selected_subtrees(self):
        synced = sync_static_to_staticfiles(subpaths=['css'])

        self.assertTrue(any(item['target'].endswith('staticfiles\\css') for item in synced))


class SurfaceRuntimeContractTests(SimpleTestCase):
    def test_build_surface_runtime_contract_keeps_backend_as_source_of_truth(self):
        contract = build_surface_runtime_contract(
            surface_behavior=build_surface_behavior(
                surface_key='student-directory',
                role_slug='Owner',
                cache_key='all',
                refresh_token='students:v1',
                bootstrap_item_count=15,
                bootstrap_has_more=True,
                hydration_mode='idle',
                hydration_page_url='/alunos/busca/paginas/',
                hydration_page_size=50,
                local_filters=['query', 'status'],
                server_filters=['payment_status'],
            ),
            asset_behavior=build_asset_behavior(
                critical_css=['students-scene'],
                deferred_css=['students-secondary-panels'],
                progressive_js=['surface-runtime', 'student-directory'],
            ),
            telemetry_key='student-directory',
            surface_budget_key='students-hot-path',
            expected_hot_path='cache-hit-after-first-load',
        )

        self.assertEqual(contract['surface_behavior']['surface_key'], 'student-directory')
        self.assertEqual(contract['surface_behavior']['scope']['role_slug'], 'Owner')
        self.assertEqual(contract['surface_behavior']['cache']['refresh_token'], 'students:v1')
        self.assertEqual(contract['surface_behavior']['bootstrap']['item_count'], 15)
        self.assertEqual(contract['surface_behavior']['hydration']['mode'], 'idle')
        self.assertEqual(contract['surface_behavior']['filters']['local'], ['query', 'status'])
        self.assertEqual(contract['surface_behavior']['filters']['server'], ['payment_status'])
        self.assertTrue(contract['surface_behavior']['invalidation']['on_refresh_token_change'])
        self.assertFalse(contract['surface_behavior']['safety']['persist_to_disk'])
        self.assertEqual(contract['asset_behavior']['progressive_js'], ['surface-runtime', 'student-directory'])
        self.assertEqual(contract['observability']['surface_budget_key'], 'students-hot-path')
