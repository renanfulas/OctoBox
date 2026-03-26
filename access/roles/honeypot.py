"""
ARQUIVO: definição do papel Honeypot.

POR QUE ELE EXISTE:
- Cria uma "identidade falsa" para atacantes identificados.
- Permite que o sistema os isole em uma realidade paralela (Shadow Reality).
"""

from .base import RoleDefinition

ROLE_HONEYPOT = 'honeypot'

HONEYPOT_PERMISSIONS = (
    'Acesso ao labirinto virtual.',
    'Visualização de dados ofuscados.',
    'Monitoramento passivo de atividades.',
)

HONEYPOT_ROLE = RoleDefinition(
    slug=ROLE_HONEYPOT,
    label='Candidato (Audit)',
    summary='Perfil em auditoria de segurança profunda.',
    capabilities=HONEYPOT_PERMISSIONS,
)
