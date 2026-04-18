<!--
ARQUIVO: mapa de autoridade e precedencia da documentacao do projeto.

TIPO DE DOCUMENTO:
- referencia operacional de documentacao

AUTORIDADE:
- alta para conflito entre docs, leitura por IA e navegacao do time

DOCUMENTO PAI:
- [../../README.md](../../README.md)

QUANDO USAR:
- quando houver duvida sobre qual doc deve vencer
- quando IA ou time precisarem decidir por onde ler primeiro
- quando um doc parecer velho, ambiguo, parcial ou em conflito com outro

POR QUE ELE EXISTE:
- evita que o time trate retrospectiva, plano, manifesto e runbook como se tivessem o mesmo peso
- reduz busca cega e interpretacao errada de docs historicos como regra viva
- cria um criterio unico para IA e humanos navegarem pela base

O QUE ESTE ARQUIVO FAZ:
1. define a hierarquia de autoridade da documentacao
2. separa documentos canonicos de snapshots, historia e inspiracao
3. registra sinais de envelhecimento e regra de desempate
4. cria um protocolo curto de leitura para IA e time

PONTOS CRITICOS:
- este mapa nao substitui evidencia do runtime, testes ou codigo real
- se um doc mudar de papel, este mapa precisa mudar junto
- links quebrados ou status antigos reduzem autoridade operacional de qualquer documento
-->

# Mapa de autoridade da documentacao

Este documento existe para resolver uma confusao comum:

nem todo doc foi feito para mandar.

Alguns docs explicam a visao.
Alguns guiam execucao.
Alguns registram historia.
Alguns so guardam uma fotografia de um momento.

Sem esse filtro, o time corre o risco de usar diario de obra como se fosse planta aprovada.

## Regra-mestra

Quando houver conflito entre docs, use esta ordem:

1. runtime real, testes e estrutura atual do codigo
2. [../../README.md](../../README.md) para produto, escopo e estado geral
3. docs canonicos de arquitetura e direcao ativa
4. planos ativos da frente atual
5. referencias tecnicas de navegacao e ownership
6. runbooks e gates operacionais de rollout
7. docs de experiencia e UX como guardrail de fachada
8. diagnosticos e relatorios como leitura auxiliar de momento
9. historico e retrospectivas como contexto, nunca como regra viva
10. inspiracao e manifestos como linguagem cultural, nunca como verdade operacional isolada

Traducao pratica:

1. se o codigo e o doc divergem, o codigo vence e o doc precisa ser corrigido
2. se dois docs divergem, vence o que tiver papel mais alto nesta hierarquia
3. se dois docs do mesmo nivel divergem, vence o mais especifico para a pergunta atual

## Hierarquia por pasta

### 1. README

Arquivo canonico:

1. [../../README.md](../../README.md)

Papel:

1. explicar o produto
2. declarar o estado geral do repositorio
3. apontar portas de entrada da documentacao

Quando vence:

1. duvida sobre o que o produto e
2. duvida sobre escopo atual
3. duvida sobre qual categoria de doc abrir primeiro

Quando perde:

1. detalhes finos de codigo, quando a referencia tecnica estiver mais especifica
2. status operacional curto de uma frente, quando existir um board ativo mais especifico

### 2. Architecture

Pasta:

1. [../architecture](../architecture)

Papel:

1. tese estrutural
2. core conceitual
3. rumo de medio e longo prazo
4. fronteiras permanentes do predio

Autoridade:

1. alta para conceito, direcao e linguagem oficial da arquitetura

Exemplos fortes:

1. [../architecture/octobox-architecture-model.md](../architecture/octobox-architecture-model.md)
2. [../architecture/octobox-conceptual-core.md](../architecture/octobox-conceptual-core.md)
3. [../architecture/django-core-strategy.md](../architecture/django-core-strategy.md)
4. [../architecture/promoted-public-facades-map.md](../architecture/promoted-public-facades-map.md)
5. [../architecture/themeOctoBox.md](../architecture/themeOctoBox.md) para tema visual oficial, assinatura e precedencia de linguagem estetica

### 3. Plans

Pasta:

1. [../plans](../plans)

Papel:

1. frente ativa
2. ordem de execucao
3. criterio de fechamento
4. convergencia tática da fase atual

Autoridade:

1. alta para o que esta sendo conduzido agora
2. media quando o plano ja foi absorvido, fechado ou superado

Regra:

1. plano ativo manda na execucao da fase
2. plano antigo ou ultrapassado vira referencia historica da frente, nao lei viva

Exemplos fortes:

1. [../plans/front-end-restructuring-guide.md](../plans/front-end-restructuring-guide.md)
2. [../plans/front-beta-closure-board.md](../plans/front-beta-closure-board.md)
3. [../plans/catalog-page-payload-presenter-blueprint.md](../plans/catalog-page-payload-presenter-blueprint.md)
4. [../plans/theme-implementation-final.md](../plans/theme-implementation-final.md) para a ordem pratica de implantacao do tema oficial

### 4. Reference

Pasta:

1. [../reference](../reference)

Papel:

1. navegacao tecnica
2. ownership
3. guias de leitura
4. checklists de manutencao

Autoridade:

1. alta para localizar arquivos e entender circuitos
2. baixa para redefinir direcao de produto ou tese arquitetural

Exemplos fortes:

1. [reading-guide.md](reading-guide.md)
2. [front-end-ownership-map.md](front-end-ownership-map.md)
3. [front-end-city-map.md](front-end-city-map.md)
4. [front-end-card-architecture.md](front-end-card-architecture.md)
5. [functional-circuits-matrix.md](functional-circuits-matrix.md)

### 4.5 Guides

Pasta:

1. [../guides](../guides)

Papel:

1. onboarding arquitetural
2. sintese do estado vivo
3. trilha curta para explicar o projeto sem mergulhar cedo demais em docs profundos

Autoridade:

1. media para orientacao
2. baixa para substituir architecture, plans ou reference especializado

Regra:

1. guides resumem e conectam
2. guides nao vencem docs canonicos de tese, plano ou ownership
3. se um guide divergir de um doc mais alto na hierarquia, o guide deve ser corrigido
4. trilhas por perfil em `guides/profiles/*` organizam onboarding e prioridade de leitura, nao ownership tecnico final

### 5. Rollout

Pasta:

1. [../rollout](../rollout)

Papel:

1. gate operacional
2. homologacao
3. deploy
4. piloto
5. validacao de campo

Autoridade:

1. alta para liberacao, checklist e operacao assistida

Exemplos fortes:

1. [../rollout/beta-internal-release-gate.md](../rollout/beta-internal-release-gate.md)
2. [../rollout/beta-role-test-agenda.md](../rollout/beta-role-test-agenda.md)

### 6. Experience

Pasta:

1. [../experience](../experience)

Papel:

1. guardrails de front e UX
2. linguagem da fachada
3. criterio de leitura e composicao visual

Autoridade:

1. alta para principios de experiencia
2. media para status operacional de momento

Regra:

1. docs conceituais daqui envelhecem devagar
2. docs com data, rodada, checklist ou viewport envelhecem rapido e devem ser tratados como snapshot
3. se um doc de experience conflitar com [../architecture/themeOctoBox.md](../architecture/themeOctoBox.md) em tema, paleta, glow, atmosfera ou assinatura visual, a arquitetura vence

### 7. Diagnostics e Reports

Pastas:

1. [../diagnostics](../diagnostics)
2. [../reports](../reports)

Papel:

1. laudo
2. fotografia de um problema
3. leitura auxiliar para decidir correcao

Autoridade:

1. media para explicar um momento
2. baixa para disputar com docs canonicos sem nova evidencia

### 8. History

Pasta:

1. [../history](../history)

Papel:

1. preservar aprendizado
2. registrar trade-offs
3. explicar como se pensou em uma fase

Autoridade:

1. baixa para decisao atual

Regra:

1. historia ensina
2. historia nao governa o runtime de hoje

### 9. Inspiration

Pasta:

1. [../inspiration](../inspiration)

Papel:

1. inspirar linguagem, visao e sentimento de produto

Autoridade:

1. muito baixa para execucao operacional

## Sinais de envelhecimento

Se um doc tiver um ou mais sinais abaixo, sua autoridade operacional cai ate ser revisado:

1. links quebrados
2. caminho de arquivo que nao existe mais
3. status temporal como `quase pronto`, `pendente`, `rodada aberta`, `data base` sem revisao posterior
4. duplicidade de estados ou conclusoes contraditorias
5. referencias a arquitetura antiga ja promovida ou reorganizada
6. evidencias muito datadas sem nova validacao

## Regras de desempate por tipo de duvida

### Produto e estado geral

Use:

1. [../../README.md](../../README.md)

### Arquitetura oficial

Use:

1. [../architecture/octobox-architecture-model.md](../architecture/octobox-architecture-model.md)
2. [../architecture/octobox-conceptual-core.md](../architecture/octobox-conceptual-core.md)
3. [../architecture/themeOctoBox.md](../architecture/themeOctoBox.md) para tema visual oficial e precedencia de linguagem

### Frente ativa do front-end

Use:

1. [../plans/front-end-restructuring-guide.md](../plans/front-end-restructuring-guide.md) para tese e estrutura
2. [../plans/front-beta-closure-board.md](../plans/front-beta-closure-board.md) para status atual de fechamento
3. [../plans/theme-implementation-final.md](../plans/theme-implementation-final.md) para a implantacao pratica do tema visual oficial

### Navegacao tecnica e ownership

Use:

1. [reading-guide.md](reading-guide.md)
2. [front-end-ownership-map.md](front-end-ownership-map.md)
3. [functional-circuits-matrix.md](functional-circuits-matrix.md)

### Beta, rollout e liberacao

Use:

1. [../rollout/beta-internal-release-gate.md](../rollout/beta-internal-release-gate.md)
2. [../rollout/beta-role-test-agenda.md](../rollout/beta-role-test-agenda.md)

### Mobile, checklist e rodada datada

Use com cautela:

1. docs com data explicita sao snapshot
2. eles ajudam a lembrar o que foi visto
3. eles nao provam o estado atual sozinhos

## Protocolo curto para IA e time

Antes de sair abrindo tudo, siga esta ordem:

1. leia o [../../README.md](../../README.md)
2. leia este mapa
3. escolha a pasta certa para a pergunta
4. leia o doc canonico da categoria
5. so depois abra docs irmaos ou historicos
6. se encontrar conflito, registre o conflito e prefira runtime mais doc de maior autoridade

## Regra final

Documento bonito nao basta.

Documento vivo e aquele que:

1. aponta para arquivos reais
2. fala do estado atual
3. manda apenas no territorio certo
4. aceita perder quando o runtime mostra outra verdade
