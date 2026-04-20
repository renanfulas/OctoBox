"""
ARQUIVO: configuracao do app de conhecimento interno.

POR QUE ELE EXISTE:
- registra o app responsavel pelo RAG interno do projeto sem contaminar dominios transacionais.

O QUE ESTE ARQUIVO FAZ:
1. declara a configuracao Django do app `knowledge`.
2. mantem a capacidade de RAG como camada de leitura acima do core.
"""

from django.apps import AppConfig


class KnowledgeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'knowledge'

