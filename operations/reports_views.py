"""
ARQUIVO: views do modulo de relatorios operacionais.

POR QUE ELE EXISTE:
- fornece o hub central para Owner e Manager acessarem a camada gerencial.

O QUE ESTE ARQUIVO FAZ:
1. Monta a view do `reports-hub.html`.
2. Garante o bloqueio para papeis indevidos.
3. Explicita o estado da camada de relatorios sem expor comandos de saida no meio da experiencia principal.
"""

from django.views.generic import TemplateView

from access.roles import ROLE_MANAGER, ROLE_OWNER
from operations.base_views import OperationBaseView
from shared_support.page_payloads import build_page_hero, build_page_reading_panel


class ReportHubView(OperationBaseView, TemplateView):
    """
    Portal gerencial do OctoBox.
    Acesso restrito para leitura da camada comercial e financeira em fase controlada.
    """

    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)
    template_name = 'operations/reports-hub.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_context = self.get_base_context()
        context.update(base_context)
        context['report_hub_focus'] = [
            {
                'label': 'Leitura comercial guardada',
                'chip_label': 'Comercial',
                'summary': 'A leitura de base, retencao e sinais comerciais segue guardada para o momento certo.',
                'pill_class': 'accent',
                'href': '#reports-commercial',
                'href_label': 'Ver camada comercial',
            },
            {
                'label': 'Leitura financeira sob vigilancia',
                'chip_label': 'Financeiro',
                'summary': 'O motor de fechamento segue pronto, mas a interface principal fica limpa para proteger a operacao diaria.',
                'pill_class': 'info',
                'href': '#reports-finance',
                'href_label': 'Ver camada financeira',
            },
            {
                'label': 'Fase atual do produto',
                'chip_label': 'Agora',
                'summary': 'O foco desta frente e clareza de uso, velocidade e acabamento antes de reabrir a camada final de saida.',
                'pill_class': 'warning',
                'href': '#reports-finance',
                'href_label': 'Ler direcao da fase',
            },
        ]
        context['report_hub_hero'] = build_page_hero(
            eyebrow='Relatorios',
            title='Camada gerencial.',
            copy='Abra a frente certa sem misturar o cofre gerencial com a operacao diaria.',
            actions=[
                {'label': 'Ver comercial', 'href': '#reports-commercial', 'kind': 'primary', 'data_action': 'jump-report-commercial'},
                {'label': 'Ver financeiro', 'href': '#reports-finance', 'kind': 'secondary', 'data_action': 'jump-report-finance'},
            ],
            aria_label='Panorama da central de relatorios',
            classes=['reports-hub-hero'],
            heading_level='h1',
            data_panel='reports-hub-hero',
        )
        context['report_hub_reading_panel'] = build_page_reading_panel(
            items=context['report_hub_focus'],
            primary_href=context['report_hub_focus'][0]['href'] if context['report_hub_focus'] else '',
            class_name='reports-hub-reading-panel',
            panel_id='reports-hub-reading-panel',
        )
        return context
