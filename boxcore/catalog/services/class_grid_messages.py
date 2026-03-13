"""
ARQUIVO: mensagens operacionais da grade de aulas.

POR QUE ELE EXISTE:
- centraliza os textos exibidos pela grade de aulas para reduzir string solta na view, form e commands.

O QUE ESTE ARQUIVO FAZ:
1. define mensagens padrao de erro e sucesso da grade.
2. oferece pequenos helpers para mensagens com dados dinamicos.
3. padroniza a comunicacao operacional da tela.

PONTOS CRITICOS:
- qualquer mudanca aqui impacta feedback visual, testes e entendimento do fluxo pela equipe.
"""

from operations.application.class_grid_messages import *