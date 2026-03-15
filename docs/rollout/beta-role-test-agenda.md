<!--
ARQUIVO: agenda pratica de testes manuais do beta por papel.

POR QUE ELE EXISTE:
- organiza uma rotina curta de validacao manual sem depender de memoria oral.
- ajuda a provar que uma funcionalidade local continua se comunicando com as outras telas.
- transforma o beta em uma operacao revisavel por circuito e por papel.

O QUE ESTE ARQUIVO FAZ:
1. define testes manuais minimos por papel.
2. aponta os circuitos cruzados que cada papel precisa validar.
3. deixa explicito quando um teste manual deve ser acompanhado de suite automatizada.

TIPO DE DOCUMENTO:
- runbook curto de validacao manual.

AUTORIDADE:
- alta para smoke funcional do beta.

DOCUMENTO PAI:
- [../reference/functional-circuits-matrix.md](../reference/functional-circuits-matrix.md)

QUANDO USAR:
- antes de homologar pacote funcional do beta.
- depois de mudancas em tela, fila, CTA, ancora ou comunicacao entre paginas.

PONTOS CRITICOS:
- este runbook nao substitui testes automatizados.
- se um papel nao tiver usuario disponivel, registrar a lacuna antes de considerar a rodada concluida.
-->

# Agenda pratica de testes manuais do beta por papel

## Regra de execucao

Cada rodada manual deve registrar:

1. papel testado
2. rota inicial usada
3. dado minimo criado ou reutilizado
4. comportamento esperado
5. paginas vizinhas conferidas no mesmo circuito

Sempre que houver mudanca funcional relevante, combine esta agenda com a suite automatizada correspondente definida em [../reference/functional-circuits-matrix.md](../reference/functional-circuits-matrix.md).

## Owner

Rota inicial:

1. `dashboard/`

Verificacoes manuais:

1. confirmar leitura geral do dashboard sem bloqueio de acesso
2. abrir atalhos principais para Alunos, Financeiro e Operacao
3. confirmar que topbar, alertas e proxima acao continuam coerentes
4. validar acesso ao admin privado quando fizer parte do pacote alterado

Circuitos vizinhos para conferir:

1. Dashboard, Alunos e Financeiro
2. Dashboard e workspaces operacionais por papel

Suite automatizada minima:

1. [boxcore/tests/test_dashboard.py](../../boxcore/tests/test_dashboard.py)
2. [boxcore/tests/test_shell_hints.py](../../boxcore/tests/test_shell_hints.py)
3. [boxcore/tests/test_security_guards.py](../../boxcore/tests/test_security_guards.py) quando a mudanca tocar acesso ou admin

## Recepcao

Rota inicial:

1. `operacao/recepcao/`

Verificacoes manuais:

1. confirmar fila de intake com ancora funcional
2. confirmar fila de pagamento pendente com ancora funcional
3. abrir link para Alunos quando o topo sinalizar intake pendente
4. validar ida e volta entre Recepcao, Dashboard e Alunos sem perder contexto operacional

Circuitos vizinhos para conferir:

1. Recepcao, Dashboard e Alunos
2. Recepcao e Financeiro para pendencia de pagamento

Suite automatizada minima:

1. [boxcore/tests/test_operations.py](../../boxcore/tests/test_operations.py)
2. [boxcore/tests/test_operations_services.py](../../boxcore/tests/test_operations_services.py)
3. [boxcore/tests/test_shell_hints.py](../../boxcore/tests/test_shell_hints.py)

## Coach

Rota inicial:

1. `operacao/coach/`

Verificacoes manuais:

1. registrar ocorrencia tecnica ou comportamental quando o pacote tocar esse fluxo
2. confirmar feedback visivel da action
3. conferir reflexo da prioridade no dashboard quando aplicavel

Circuitos vizinhos para conferir:

1. Coach e Dashboard
2. Coach e historico operacional do aluno quando a mudanca tocar registro de ocorrencia

Suite automatizada minima:

1. [boxcore/tests/test_operations.py](../../boxcore/tests/test_operations.py)
2. [boxcore/tests/test_operations_domain.py](../../boxcore/tests/test_operations_domain.py)
3. [boxcore/tests/test_shell_hints.py](../../boxcore/tests/test_shell_hints.py) quando houver reflexo no shell

## Gerente

Rota inicial:

1. `operacao/gerente/`

Verificacoes manuais:

1. confirmar leitura consolidada de cards e contadores
2. abrir CTA principais para filas ou telas relacionadas
3. verificar se a composicao continua coerente com Dashboard e workspaces por papel

Circuitos vizinhos para conferir:

1. Gerente e Dashboard
2. Gerente e workspaces operacionais impactados pela mudanca

Suite automatizada minima:

1. [boxcore/tests/test_operations.py](../../boxcore/tests/test_operations.py)
2. [boxcore/tests/test_shell_hints.py](../../boxcore/tests/test_shell_hints.py)
3. [boxcore/tests/test_page_payloads.py](../../boxcore/tests/test_page_payloads.py) quando o pacote tocar hero ou behavior

## Alunos

Rota inicial:

1. `alunos/`

Verificacoes manuais:

1. localizar aluno por busca e abrir ficha
2. validar matricula, intake ou pagamento quando o pacote tocar mutacao desses fluxos
3. confirmar que links cruzados vindos do topo ou dashboard continuam pousando no lugar certo

Circuitos vizinhos para conferir:

1. Alunos, Dashboard e Recepcao
2. Alunos e Financeiro

Suite automatizada minima:

1. [boxcore/tests/test_catalog.py](../../boxcore/tests/test_catalog.py)
2. [boxcore/tests/test_students_domain.py](../../boxcore/tests/test_students_domain.py)
3. [boxcore/tests/test_shell_hints.py](../../boxcore/tests/test_shell_hints.py)

## Financeiro

Rota inicial:

1. `financeiro/`

Verificacoes manuais:

1. abrir central financeira e confirmar leitura de inadimplencia
2. disparar ou revisar comunicacao financeira quando o pacote tocar cobranca
3. validar se alertas do topo e atalhos continuam coerentes com Recepcao e Dashboard

Circuitos vizinhos para conferir:

1. Financeiro, Dashboard e Recepcao
2. Financeiro e Alunos quando houver reflexo em pagamento ou matricula

Suite automatizada minima:

1. [boxcore/tests/test_finance.py](../../boxcore/tests/test_finance.py)
2. [boxcore/tests/test_catalog_services.py](../../boxcore/tests/test_catalog_services.py)
3. [boxcore/tests/test_shell_hints.py](../../boxcore/tests/test_shell_hints.py)

## Dashboard

Rota inicial:

1. `dashboard/`

Verificacoes manuais:

1. confirmar KPIs, cards e alertas principais
2. abrir atalhos para Alunos, Financeiro e fila operacional afetada
3. verificar se cada CTA aponta para a ancora ou destino certo

Circuitos vizinhos para conferir:

1. Dashboard, Alunos e Financeiro
2. Dashboard e Recepcao
3. Dashboard e Coach quando o pacote tocar prioridade operacional

Suite automatizada minima:

1. [boxcore/tests/test_dashboard.py](../../boxcore/tests/test_dashboard.py)
2. [boxcore/tests/test_page_payloads.py](../../boxcore/tests/test_page_payloads.py)
3. [boxcore/tests/test_shell_hints.py](../../boxcore/tests/test_shell_hints.py)

## API publica

Rota inicial:

1. `api/`
2. `api/v1/`

Verificacoes manuais:

1. confirmar manifesto e health sem regressao de contrato
2. se o pacote tocar autocomplete, validar resposta autenticada com termo real
3. confirmar que a mudanca nao vazou detalhe visual ou HTML para a fronteira publica

Circuitos vizinhos para conferir:

1. API e consumo interno de busca de alunos quando aplicavel
2. API e regras de seguranca quando tocar autenticacao ou throttling

Suite automatizada minima:

1. [boxcore/tests/test_api.py](../../boxcore/tests/test_api.py)
2. [boxcore/tests/test_security_guards.py](../../boxcore/tests/test_security_guards.py) quando tocar autenticacao, throttling ou autocomplete

## Integracao WhatsApp

Rota inicial:

1. nao depende de rota visual fixa; validar pelo fluxo funcional ou pelo ponto de entrada que disparou a integracao

Verificacoes manuais:

1. confirmar que mensagem inbound nao duplica log quando reprocessada
2. confirmar conciliacao correta entre contato, aluno e intake
3. confirmar que payload sensivel nao ficou exposto em log persistido

Circuitos vizinhos para conferir:

1. Integracao e Communications
2. Integracao e Financeiro quando houver cobranca
3. Integracao e Recepcao quando houver intake ou atendimento operacional

Suite automatizada minima:

1. [boxcore/tests/test_integrations.py](../../boxcore/tests/test_integrations.py)
2. suite funcional do circuito impactado

## Encerramento da rodada manual

1. registrar papel, rota e resultado
2. anotar qualquer divergencia entre tela local e tela vizinha
3. se a divergencia envolver shell, topo, CTA ou ancora, abrir ajuste no circuito completo e nao apenas na pagina isolada