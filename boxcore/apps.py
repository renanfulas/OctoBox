"""
ARQUIVO: configuração oficial do app legado boxcore no Django.

POR QUE ELE EXISTE:
- Mantem a ancora historica de estado do Django enquanto schema, app_label e migrations ainda pertencem a boxcore.

O QUE ESTE ARQUIVO FAZ:
1. Define o nome tecnico historico do app.
2. Define o tipo padrão de chave primária.
3. Deixa explicito que boxcore nao e mais o centro do runtime, e sim a ancora legado de estado.

PONTOS CRITICOS:
- Trocar o nome ou label aqui sem um plano de migracao quebra imports, admin e migrations.
"""

from django.apps import AppConfig


class BoxcoreConfig(AppConfig):
    name = 'boxcore'
    verbose_name = 'Boxcore Legacy State'
