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
from shared_support.static_assets import resolve_runtime_css_paths


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
            shell={
                'shell_action_buttons': [
                    {'label': 'Prioridade', 'href': '#student-priority-board', 'summary': 'Ler quem pede acao agora.'},
                ]
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
        self.assertEqual(result['shell_action_buttons'], payload['shell']['shell_action_buttons'])
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
        self.assertEqual(result['page_assets'], result['current_page_assets'])

    def test_resolve_runtime_css_paths_expands_manifest_imports(self):
        resolved = resolve_runtime_css_paths(['css/design-system.css'])

        self.assertIn('css/design-system/tokens.css', resolved)
        self.assertIn('css/design-system/compass.css', resolved)
        self.assertIn('css/design-system/components/hero.css', resolved)
        self.assertNotIn('css/design-system.css', resolved)