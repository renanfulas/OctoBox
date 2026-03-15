<!--
ARQUIVO: checklist operacional de PR por circuito funcional.

POR QUE ELE EXISTE:
- transforma a matriz de ownership em rotina objetiva de revisao.
- evita aprovar mudanca local que quebra comunicacao cruzada.
- reduz dependencia de memoria individual na revisao do beta.

O QUE ESTE ARQUIVO FAZ:
1. define um gate curto de PR para circuitos funcionais.
2. separa checagens comuns de checagens por tipo de impacto.
3. aponta quando usar o checklist visual de front junto com este documento.

TIPO DE DOCUMENTO:
- checklist operacional de revisao.

AUTORIDADE:
- alta para PRs que alteram comportamento funcional do beta.

DOCUMENTO PAI:
- [functional-circuits-matrix.md](functional-circuits-matrix.md)

QUANDO USAR:
- antes de abrir PR.
- antes de aprovar PR que altera fluxo, CTA, ancora, payload ou integracao.

PONTOS CRITICOS:
- este checklist complementa o checklist visual de front, nao substitui.
- se a mudanca toca mais de um papel, a revisao precisa olhar o circuito inteiro.
-->

# Checklist de PR por circuito funcional

Use este documento junto com [../experience/front-pr-checklist.md](../experience/front-pr-checklist.md) quando a alteracao for visual ou de interface.

## Gate comum

1. o dono local da funcionalidade esta claro na PR
2. os contratos compartilhados afetados foram citados ou alterados explicitamente
3. a PR deixa claro qual circuito vizinho pode ser impactado
4. a suite minima do circuito foi executada
5. nao houve mudanca oculta de ancora, href estrutural ou `data-*` sem revisao da tela de destino

## Se a mudanca tocar payload, hero, assets ou behavior da tela

1. revisar [shared_support/page_payloads.py](../../shared_support/page_payloads.py)
2. executar [boxcore/tests/test_page_payloads.py](../../boxcore/tests/test_page_payloads.py)
3. executar a suite local da funcionalidade

## Se a mudanca tocar prioridade, alerta, pulse chip ou CTA cruzado

1. revisar [access/context_processors.py](../../access/context_processors.py)
2. revisar [access/shell_actions.py](../../access/shell_actions.py)
3. executar [boxcore/tests/test_shell_hints.py](../../boxcore/tests/test_shell_hints.py)
4. executar a suite da funcionalidade dona
5. executar a suite da tela vizinha mais diretamente afetada

## Se a mudanca tocar action, workflow, mutacao ou fila

1. executar a suite HTTP local
2. executar a suite de dominio ou service correspondente
3. se a mutacao muda contagem, alerta ou fila visivel, executar tambem [boxcore/tests/test_shell_hints.py](../../boxcore/tests/test_shell_hints.py)

## Se a mudanca tocar API publica

1. revisar [api/urls.py](../../api/urls.py) e [api/v1/urls.py](../../api/v1/urls.py)
2. executar [boxcore/tests/test_api.py](../../boxcore/tests/test_api.py)
3. se tocar autenticacao, throttling ou autocomplete, executar [boxcore/tests/test_security_guards.py](../../boxcore/tests/test_security_guards.py)
4. verificar se a documentacao ou manifesto publico continuou coerente

## Se a mudanca tocar integracao externa

1. revisar contratos e fachada publica da integracao
2. executar [boxcore/tests/test_integrations.py](../../boxcore/tests/test_integrations.py)
3. validar idempotencia, vinculacao de identidade e saneamento de payload
4. se a integracao gerar efeito em recepcao, financeiro ou alunos, executar tambem a suite do circuito afetado

## Se a mudanca introduzir ou alterar job assincrono

1. confirmar que o job nao concentrou regra de HTTP ou template
2. confirmar que o job e reexecutavel e preferencialmente idempotente
3. exigir cobertura no dominio dono no mesmo pacote da PR
4. se o job acionar integracao, executar tambem [boxcore/tests/test_integrations.py](../../boxcore/tests/test_integrations.py)

## Fechamento rapido para aprovacao

1. a funcionalidade continua facil de localizar por leitura direta
2. a mudanca melhorou ou preservou a comunicacao entre paginas
3. os testes escolhidos fazem sentido para o risco real da PR
4. se houver papel afetado, existe evidenca de validacao desse papel