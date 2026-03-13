<!--
ARQUIVO: roteiro operacional curto para sair da ideia do Beam e entrar na execucao disciplinada da convergencia do projeto.

POR QUE ELE EXISTE:
- transforma o guia de prontidao em um passo a passo pratico e facil de seguir.
- permite comecar agora sem depender de interpretacao ampla do documento principal.

O QUE ESTE ARQUIVO FAZ:
1. quebra a trilha em passos executaveis.
2. define a ordem real de ataque.
3. registra a primeira largada pratica da Recepcao.

TIPO DE DOCUMENTO:
- execucao ativa

AUTORIDADE:
- media, subordinada ao guia de prontidao

DOCUMENTO PAI:
- [vertical-sky-beam-readiness-guide.md](vertical-sky-beam-readiness-guide.md)

QUANDO USAR:
- quando a duvida for qual passo executar agora, em qual ordem e com qual saida concreta

PONTOS CRITICOS:
- este roteiro nao substitui o guia de prontidao; ele e a traducao operacional dele.
- pular etapas volta a criar descompasso entre front, UX, Center e dominio.
-->

# Roteiro de execucao do Vertical Sky Beam

## Como ler este roteiro

Use este documento como trilha curta de execucao.

Regra de autoridade:

1. o [vertical-sky-beam-readiness-guide.md](vertical-sky-beam-readiness-guide.md) define a tese, os guardrails e o criterio de pronto
2. este roteiro define apenas a ordem ativa de ataque, as saidas esperadas e o proximo passo pratico

Regra central:

1. nao avancar por entusiasmo
2. avancar por prova concreta de convergencia

## Passo a passo

### Passo 1: escolher a capacidade piloto

Objetivo:

1. definir uma frente visivel onde a convergencia sera provada

Escolha atual:

1. Recepcao

Sinal de pronto:

1. ficou claro que a Recepcao atravessa shell, dashboard, workspace, catalogo e fronteira de papel

### Passo 2: fazer o baseline honesto

Objetivo:

1. mapear o estado real da Recepcao antes de tentar melhorar qualquer coisa

Checklist:

1. listar telas e rotas da Recepcao
2. listar onde a experiencia ainda muda de idioma visual
3. listar onde a UX ainda muda de logica mental
4. listar bypasses fora do CENTER
5. listar residuos de `boxcore` que ainda aparecem na capacidade

Sinal de pronto:

1. existe uma fotografia fria da capacidade, sem fantasia

### Passo 3: definir o contrato unico da capacidade

Objetivo:

1. fazer a Recepcao se comportar como uma capacidade unica e nao como varias telas parentes

Checklist:

1. definir a hierarquia padrao das paginas
2. definir CTA principal e CTA secundario por contexto
3. definir estados vazios, alertas e confirmacoes
4. definir a regra de formulários curtos e atendimento rapido
5. definir a mesma linguagem de copy para dashboard, workspace e atalhos

Sinal de pronto:

1. qualquer nova tela da Recepcao consegue nascer pelo mesmo contrato

### Passo 4: consolidar o Front Display Wall

Objetivo:

1. fazer a frente visual da capacidade parecer unificada

Checklist:

1. fechar contratos explicitos de CSS
2. reduzir dependencias de heranca fragil
3. alinhar ritmo visual entre cards, grids e trilhos
4. revisar tablet e mobile
5. garantir que a pagina continue clara em poucos segundos de leitura

Sinal de pronto:

1. a Recepcao parece um modulo coeso para quem usa

### Passo 5: consolidar a UX como regra

Objetivo:

1. impedir que a capacidade continue dependendo de interpretacao excessiva

Checklist:

1. revisar prioridades visuais
2. revisar microcopy por papel
3. revisar estados de erro e vazio
4. revisar formulários para limitar e orientar melhor a digitacao
5. revisar se a proxima acao continua obvia em toda a jornada

Sinal de pronto:

1. o usuario entende o que fazer sem precisar reaprender a cada tela

### Passo 6: puxar a borda para o CENTER

Objetivo:

1. fazer as entradas da capacidade passarem pelos corredores oficiais

Checklist:

1. identificar entradas externas relevantes
2. reancorar views e actions nas facades corretas
3. reduzir servicos historicos a adaptadores finos
4. bloquear o nascimento de novos atalhos fora do CENTER

Sinal de pronto:

1. a borda deixa de conhecer o miolo em excesso

### Passo 7: limpar o resíduo de boxcore na capacidade

Objetivo:

1. provar que a convergencia tambem vale no fundo estrutural

Checklist:

1. localizar imports publicos de `boxcore`
2. trocar por surfaces de dominio
3. registrar o que ainda precisa ficar como ancora historica
4. impedir recaida em codigo novo

Sinal de pronto:

1. a capacidade deixa de depender mentalmente de `boxcore` no dia a dia

### Passo 8: testar a capacidade como organismo

Objetivo:

1. validar que front, UX, rotas, regras e permissao conversam entre si

Checklist:

1. testes HTTP da capacidade
2. testes de permissao e navegacao
3. testes de fluxo principal
4. revisao visual humana
5. checagem de manutencao barata apos uma pequena alteracao real

Sinal de pronto:

1. corrigir ou expandir a capacidade custa menos do que antes

### Passo 9: repetir em outra capacidade

Objetivo:

1. provar que o metodo funciona alem da Recepcao

Ordem recomendada:

1. Manager
2. Financeiro
3. Alunos

Sinal de pronto:

1. duas ou mais capacidades relevantes ja evoluem pelo mesmo metodo

### Passo 10: avaliar se o Beam de consagracao foi merecido

Objetivo:

1. decidir se a obra realmente alcancou sincronizacao estrutural rara

Perguntas finais:

1. o front conversa com a operacao sem atrito grande?
2. a UX virou disciplina de produto?
3. o CENTER passou a organizar a borda real?
4. `boxcore` deixou de ser muleta cotidiana?
5. o novo entra no sistema sem improviso?

Se essas respostas estiverem fortes em mais de uma capacidade, o projeto se aproxima do Beam de consagracao.

## Backlog ativo imediato

Inicio recomendado imediato:

1. executar o baseline honesto da Recepcao
2. registrar incoerencias de front e UX
3. mapear bypasses fora do CENTER
4. mapear residuos de `boxcore`
5. transformar isso em backlog curto da Fase 1

## Saida minima desta rodada

Ao fim da primeira rodada, precisamos sair com quatro artefatos:

1. mapa da capacidade Recepcao
2. lista de inconsistencias visuais e de UX
3. lista de bypasses e residuos historicos
4. plano curto de ataque para a Fase 1

O baseline oficial desta rodada agora fica registrado em [reception-phase0-baseline.md](reception-phase0-baseline.md).