<!--
ARQUIVO: classificacao oficial do espelho local OctoBox como legado isolado.

TIPO DE DOCUMENTO:
- referencia tecnica de ownership e escopo

AUTORIDADE:
- media para navegacao, tooling local e higiene do repositorio

DOCUMENTO PAI:
- [../../README.md](../../README.md)

QUANDO USAR:
- quando houver duvida sobre o papel da pasta `OctoBox/`
- quando testes, tooling ou agentes encontrarem o espelho local
- quando for decidir entre manter, isolar, arquivar ou remover o espelho

POR QUE ELE EXISTE:
- evita que o espelho seja confundido com o runtime principal
- registra que o espelho ainda existe por compatibilidade local e historico de testes
- cria uma classificacao explicita de legado para reduzir ambiguidade

PONTOS CRITICOS:
- este documento nao promove o espelho a runtime canonico
- o espelho nao deve receber evolucao funcional nova por padrao
- qualquer plano de remocao fisica precisa validar primeiro tooling, testes e uso humano residual
-->

# OctoBox Mirror Legacy Status

## Status oficial

A pasta `OctoBox/` deve ser tratada como:

1. espelho legado local
2. nao canonico para o runtime principal
3. isolado por padrao
4. mantido apenas enquanto ainda existir valor residual de compatibilidade, consulta ou suporte a tooling

Em linguagem simples:

1. ela e uma fotografia grande do predio antigo
2. a operacao atual mora na raiz do repositorio
3. o espelho nao manda na obra viva

## O que `OctoBox/` nao e

`OctoBox/` nao deve ser lido como:

1. segunda raiz oficial do produto
2. lugar padrao para novas features
3. fonte canonica de documentacao
4. caminho preferencial para depuracao do runtime atual

## O que `OctoBox/` ainda e

Hoje o espelho ainda pode ter valor como:

1. artefato local de referencia historica
2. superficie residual para compatibilidade de testes e descoberta de tooling
3. snapshot de organizacao anterior util para comparacao

## Regra de navegacao

Quando houver duvida sobre onde trabalhar:

1. prefira a raiz do repositorio
2. prefira apps reais como `access`, `catalog`, `operations`, `students`, `finance`, `auditing`, `communications`, `api`, `integrations` e `jobs`
3. consulte `OctoBox/` apenas quando a pergunta for claramente sobre legado, espelho, compatibilidade ou evidencia historica

## Regras de manutencao

### Permitido

1. correcoes minimas para impedir quebra de tooling local
2. ajustes pequenos para compatibilidade de teste
3. consulta historica e comparativa

### Proibido por padrao

1. desenvolver feature nova primeiro no espelho
2. corrigir bug do runtime principal apenas no espelho
3. deixar o espelho divergir silenciosamente e depois tratá-lo como fonte de verdade
4. abrir novos docs canonicos apontando o espelho como raiz principal

## Criterio de permanencia temporaria

O espelho so continua existindo enquanto pelo menos uma destas condicoes for verdadeira:

1. ainda interfere na descoberta de testes ou tooling local
2. ainda e usado como referencia humana de comparacao
3. ainda nao existe uma rodada segura de isolamento ou descarte final

## Criterio de saida futura

O espelho vira candidato real a remocao fisica quando:

1. nenhum fluxo de teste depender mais dele
2. nenhum script, agente ou pessoa precisar consultá-lo como apoio
3. o time aceitar explicitamente sua aposentadoria
4. houver validacao final de que a remocao nao quebra onboarding, CI ou navegacao local

## Relacao com os `.specs`

O espelho ja apareceu como problema real de tooling em:

1. [../../.specs/features/octobox-mirror-pytest-alignment/README.md](../../.specs/features/octobox-mirror-pytest-alignment/README.md)
2. [../../.specs/features/octobox-mirror-pytest-alignment/context.md](../../.specs/features/octobox-mirror-pytest-alignment/context.md)

Isso reforca a classificacao correta:

1. legado residual
2. nao runtime principal
3. merece isolamento consciente, nao esquecimento
