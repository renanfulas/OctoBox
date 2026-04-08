"""
ARQUIVO: teste da hierarquia de prioridade visual do reading panel do dashboard.

POR QUE ELE EXISTE:
- protege a regra de produto que define qual card pode ocupar o slot dominante.

O QUE ESTE ARQUIVO FAZ:
1. valida a ordem de prioridade emergency > warning > risk.
2. garante que cards nao acionaveis nao ocupem o slot.
3. confirma que a tela pode ficar limpa quando nao houver nada acionavel.

PONTOS CRITICOS:
- se este teste quebrar, a leitura dominante do dashboard pode voltar a competir no mesmo espaco.
"""
import os
import sys
import unittest


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dashboard.presentation import _select_dashboard_reading_cards


class DashboardReadingPriorityTest(unittest.TestCase):
    def test_emergency_wins_over_warning_and_risk(self):
        cards = [
            {'severity': 'warning', 'is_actionable': True},
            {'severity': 'risk', 'is_actionable': True},
            {'severity': 'emergency', 'is_actionable': True},
        ]

        selected = _select_dashboard_reading_cards(cards)

        self.assertEqual([card['severity'] for card in selected], ['emergency'])

    def test_warning_wins_when_emergency_is_not_actionable(self):
        cards = [
            {'severity': 'emergency', 'is_actionable': False},
            {'severity': 'warning', 'is_actionable': True},
            {'severity': 'risk', 'is_actionable': True},
        ]

        selected = _select_dashboard_reading_cards(cards)

        self.assertEqual([card['severity'] for card in selected], ['warning'])

    def test_risk_wins_when_higher_priorities_are_not_actionable(self):
        cards = [
            {'severity': 'emergency', 'is_actionable': False},
            {'severity': 'warning', 'is_actionable': False},
            {'severity': 'risk', 'is_actionable': True},
        ]

        selected = _select_dashboard_reading_cards(cards)

        self.assertEqual([card['severity'] for card in selected], ['risk'])

    def test_no_card_is_selected_when_everything_is_quiet(self):
        cards = [
            {'severity': 'emergency', 'is_actionable': False},
            {'severity': 'warning', 'is_actionable': False},
            {'severity': 'risk', 'is_actionable': False},
        ]

        selected = _select_dashboard_reading_cards(cards)

        self.assertEqual(selected, [])


if __name__ == '__main__':
    unittest.main()
