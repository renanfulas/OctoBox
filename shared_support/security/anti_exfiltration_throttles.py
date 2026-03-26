"""
ARQUIVO: Camada Throttling Anti-Vazamento de Dados (Anti-Leaking).

POR QUE ELE EXISTE:
- Prevenir Roubo de Dados através de automação de interface (Scraping Visual).
- Regular a Exportação Maciça de dados do banco corporativo do OctoBox.

O QUE ESTE ARQUIVO FAZ:
1. DataExfiltrationThrottle: Disparado em visualização individual de aluno. Corta bots e acessos furiosos.
2. MassExportThrottle: Impede que a base inteira seja extraída em minutos de repetidas tentativas ou scripts escondidos.

PONTOS CRITICOS:
- Essas defesas protegem a base de Leads e de Alunos de serem sequestradas por ex-funcionários.
"""

from rest_framework.throttling import UserRateThrottle
import logging

class DataExfiltrationThrottle(UserRateThrottle):
    """
    Ratelimit de visualização rápida em abas de conteúdo único.
    Dificulta o uso de "Scrapers".
    Ex: Abrir 60 perfis de alunos em 5 minutos.
    """
    scope = 'anti_exfiltration'
    rate = '60/5m'


class MassExportThrottle(UserRateThrottle):
    """
    Ratelimit para rotas de extração (Excel/CSV).
    Trava o botão de download para ataques volumosos de extração.
    Ex: Emitir 2 planilhas inteiras na mesma hora.
    """
    scope = 'mass_export'
    rate = '2/hour'

__all__ = ['DataExfiltrationThrottle', 'MassExportThrottle']
