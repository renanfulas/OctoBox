"""
ARQUIVO: rotas das paginas visuais de catalogo.

POR QUE ELE EXISTE:
- Organiza as entradas das telas leves de alunos, financeiro e grade fora do admin.

O QUE ESTE ARQUIVO FAZ:
1. Publica a pagina de alunos e o fluxo leve de cadastro/edicao.
2. Publica as acoes diretas de pagamento e matricula por aluno.
3. Publica exportacoes CSV/PDF de alunos e financeiro.
4. Publica a central visual de financeiro, a acao operacional de comunicacao e a edicao leve de planos.
5. Publica a grade visual de aulas.

PONTOS CRITICOS:
- Estas rotas sustentam a navegacao principal de operacao diaria e precisam continuar estaveis.
"""

from catalog.urls import *