"""
ARQUIVO: namespace do app intelligence_network.

POR QUE ELE EXISTE:
- hub de rede cross-tenant (Onda 8 do plano de ML de leads): agregados
  anonimos de canal por cohort de box, para benchmark comparativo entre
  boxes sem nunca expor dado individual de aluno ou lead.

PONTOS CRITICOS:
- app SHARED (schema public), nao TENANT — precedente: student_identity.
- dado cru NUNCA sobe para ca. So contagem agregada, com piso de amostra.
"""
