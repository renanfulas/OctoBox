"""
ARQUIVO: configuracao do app students.

POR QUE ELE EXISTE:
- transforma students em app Django leve para consolidar contratos, infraestrutura e superficies de dominio.

O QUE ESTE ARQUIVO FAZ:
1. registra o app students no projeto.

PONTOS CRITICOS:
- nesta fase o app nao assume app_label nem migrations dos modelos historicos.
"""

from django.apps import AppConfig


class StudentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'students'
    verbose_name = 'Students'
