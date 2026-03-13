"""
ARQUIVO: views da area de alunos do catalogo.

POR QUE ELE EXISTE:
- Agrupa a camada HTTP ligada a diretorio, cadastro leve e acoes da ficha do aluno.

O QUE ESTE ARQUIVO FAZ:
1. Renderiza o diretorio de alunos e suas exportacoes.
2. Orquestra o fluxo leve de criacao e edicao do aluno.
3. Dispara acoes de pagamento e matricula a partir da ficha.

PONTOS CRITICOS:
- Qualquer regressao aqui afeta o principal fluxo operacional do produto.
"""

from catalog.views.student_views import *