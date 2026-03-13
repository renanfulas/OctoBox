"""
ARQUIVO: rotas das áreas operacionais por papel.

POR QUE ELE EXISTE:
- Mantém a navegação de Owner, DEV, Manager e Coach em um módulo próprio.

O QUE ESTE ARQUIVO FAZ:
1. Redireciona o usuário para sua área principal.
2. Publica telas operacionais específicas por papel.
3. Expõe ações exclusivas de manager e coach.
4. Mantém uma rota técnica separada para DEV.

PONTOS CRITICOS:
- Mudanças aqui afetam o fluxo operacional por papel.
- As rotas precisam continuar alinhadas com as restrições declaradas nas views.
"""

from operations.urls import *