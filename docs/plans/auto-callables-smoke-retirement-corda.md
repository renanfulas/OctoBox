<!--
ARQUIVO: CORDA curto para aposentar o teste auto-callables e substitui-lo por smoke estrutural honesto.

TIPO DE DOCUMENTO:
- plano curto de refatoracao de testes
- estrategia de smoke estrutural

AUTORIDADE:
- alta para a frente de substituicao de `tests/test_auto_callables.py`

DOCUMENTOS PAIS:
- [../../README.md](../../README.md)
- [../reference/documentation-authority-map.md](../reference/documentation-authority-map.md)
- [test-failures-stabilization-corda.md](test-failures-stabilization-corda.md)

QUANDO USAR:
- quando `tests/test_auto_callables.py` falhar ou produzir ruido estrutural
- quando a equipe quiser um smoke de estrutura mais confiavel que "executar tudo sem argumentos"

POR QUE ELE EXISTE:
- evita tratar chamada aleatoria de callables como se fosse garantia de runtime
- substitui um teste com side effects perigosos por checks de boot mais honestos
-->

# C.O.R.D.A. - Retirar `test_auto_callables.py` com seguranca

## C - Contexto

Hoje `tests/test_auto_callables.py`:

1. percorre modulos demais
2. chama funcoes publicas sem contrato
3. instancia classes sem ownership
4. aciona side effects como `manage.py main()`, seeds e corrotinas async do ORM

Em linguagem simples:

1. ele aperta botoes aleatorios do predio e chama isso de inspeção

## O - Objetivo

Substituir `test_auto_callables.py` por uma estrategia de smoke estrutural honesta, que valide o runtime principal sem executar callables arbitrarios.

## R - Riscos

1. manter o teste atual perpetua falsos negativos e side effects perigosos
2. remover sem substituto reduz cobertura estrutural

## D - Direcao

### Tese central

Trocar "executar callables sem args" por tres smokes menores:

1. smoke de import do runtime vivo
2. smoke de `manage.py check`
3. smoke de comandos/entrypoints explicitamente permitidos

### Contrato alvo

1. cada smoke deve ter escopo claro
2. nada de chamar callables arbitrarios
3. entrypoints com side effect precisam allowlist explicita

## A - Acoes

### Onda 0

1. marcar `tests/test_auto_callables.py` como candidato a aposentadoria
2. registrar os side effects concretos que hoje ele dispara

### Onda 1

1. criar um smoke estrutural de boot/import com allowlist
2. criar ou reaproveitar smoke de `manage.py check`
3. criar smoke opcional de comandos seguros com lista explicita

### Onda 2

1. remover `test_auto_callables.py` ou reduzir para um wrapper que falha com mensagem orientando o novo trilho

## Prompt operacional

Objetivo:

1. aposentar `tests/test_auto_callables.py`
2. manter cobertura estrutural sem side effects aleatorios

Constraints:

1. nao chamar callables arbitrarios
2. preferir allowlists explicitas
3. explicar o que a nova estrategia garante e o que ela nao garante

