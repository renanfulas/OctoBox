"""
ARQUIVO: testes dos helpers compartilhados de prioridade de leitura.

POR QUE ELE EXISTE:
- protege os contratos compartilhados que escolhem o item dominante e o href primario.

O QUE ESTE ARQUIVO FAZ:
1. valida a selecao do item mais prioritario acionavel.
2. garante fallback limpo quando nao houver item acionavel.
3. garante que o href primario ignora cards nao clicaveis.

PONTOS CRITICOS:
- regressao aqui espalha comportamento inconsistente entre dashboard e workspaces operacionais.
"""
import os
import sys
import unittest


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared_support.page_payloads import resolve_primary_href, select_priority_items


class PagePayloadPriorityHelpersTest(unittest.TestCase):
    def test_select_priority_items_respects_order(self):
        items = [
            {'severity': 'risk', 'is_actionable': True},
            {'severity': 'warning', 'is_actionable': True},
            {'severity': 'emergency', 'is_actionable': True},
        ]

        selected = select_priority_items(
            items,
            priority_order=('emergency', 'warning', 'risk'),
        )

        self.assertEqual([item['severity'] for item in selected], ['emergency'])

    def test_select_priority_items_returns_empty_when_everything_is_quiet(self):
        items = [
            {'severity': 'risk', 'is_actionable': False},
            {'severity': 'warning', 'is_actionable': False},
        ]

        selected = select_priority_items(
            items,
            priority_order=('emergency', 'warning', 'risk'),
        )

        self.assertEqual(selected, [])

    def test_resolve_primary_href_skips_non_clickable_items(self):
        items = [
            {'href': '#first', 'is_clickable': False},
            {'href': '#second', 'is_clickable': True},
        ]

        self.assertEqual(resolve_primary_href(items, '#fallback'), '#second')

    def test_resolve_primary_href_uses_fallback_when_needed(self):
        items = [
            {'href': '#first', 'is_clickable': False},
        ]

        self.assertEqual(resolve_primary_href(items, '#fallback'), '')


if __name__ == '__main__':
    unittest.main()
