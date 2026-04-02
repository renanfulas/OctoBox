# Design

## Decisao

Adicionar `OctoBox/config/settings/test.py` espelhando o contrato de teste do projeto principal:

1. ambiente de desenvolvimento seguro para testes
2. cache em memoria
3. sqlite em memoria
4. celery eager

## Motivo

Isso resolve a raiz do erro sem criar um desvio artificial no `pytest.ini`.
