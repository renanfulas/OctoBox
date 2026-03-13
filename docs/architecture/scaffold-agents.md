<!--
ARQUIVO: formalizacao dos Scaffold Agents como suporte temporario de transicao, observacao e protecao durante a construcao arquitetural.

TIPO DE DOCUMENTO:
- direcao arquitetural satelite

AUTORIDADE:
- alta

DOCUMENTO PAI:
- [octobox-architecture-model.md](octobox-architecture-model.md)

QUANDO USAR:
- quando a duvida for como admitir mecanismos temporarios sem confundi-los com a arquitetura final

POR QUE ELE EXISTE:
- separa explicitamente o que e arquitetura final do que e mecanismo temporario de construcao.
- impede que bypasses, observadores e protecoes de transicao virem parte permanente do predio.

O QUE ESTE ARQUIVO FAZ:
1. define o que sao os Scaffold Agents.
2. explica como eles se relacionam com rapeis, Center Layer e Signal Mesh.
3. estabelece regras de entrada, uso e remocao desses agentes.

PONTOS CRITICOS:
- Scaffold Agents nao pertencem ao nucleo final.
- se nao tiverem criterio de remocao, viram remendo cristalizado e pioram a arquitetura.
-->

# Scaffold Agents

## Tese central

Durante a construcao arquitetural do OctoBox, alguns caminhos excepcionais continuam existindo.

Esses caminhos nao fazem parte do predio final. Eles existem para permitir transicao segura enquanto a estrutura oficial ainda esta sendo erguida.

Os elementos que operam nesses caminhos foram nomeados como `Scaffold Agents`.

Em linguagem simples:

1. eles sao o andaime inteligente da obra
2. ajudam a construir
3. ajudam a observar risco
4. ajudam a proteger transicoes fragilizadas
5. saem quando o predio estiver pronto

## O que sao os Scaffold Agents

Scaffold Agents sao componentes temporarios de suporte que operam sobre caminhos de transicao.

Eles podem:

1. observar bypasses historicos
2. detectar risco em fluxos ainda nao consolidados
3. proteger interfaces antigas durante migracao
4. registrar sinais de fragilidade da transicao
5. ajudar a conduzir trafego de forma segura ate que o corredor oficial fique pronto

Eles nao existem para:

1. virar parte do dominio
2. substituir o CENTER
3. substituir a Signal Mesh
4. virar solucao definitiva de arquitetura

## Relacao com os rapeis

Os rapeis representam caminhos excepcionais de compatibilidade e transicao.

Os Scaffold Agents sao os operadores temporarios desses caminhos.

Relacao correta:

1. rapel = caminho excepcional
2. scaffold agent = suporte temporario que ajuda esse caminho a nao quebrar o predio

Regra:

1. nao existe Scaffold Agent sem contexto de transicao
2. se o caminho deixa de ser transitorio, o rapel precisa ser removido ou oficializado

## Relacao com o Center Layer

O `Center Layer` e estrutura permanente.

Ele representa a entrada oficial entre o nivel 1 de acesso e o nivel 2 de nucleo interno.

Scaffold Agents nao substituem esse papel.

O que eles fazem em relacao ao CENTER:

1. protegem o periodo anterior a consolidacao completa do CENTER
2. ajudam a puxar entradas antigas para a porta oficial
3. observam onde ainda existe bypass fora do hall principal

Resumo:

1. o CENTER fica
2. o Scaffold Agent sai

## Relacao com a Signal Mesh

A `Signal Mesh` tambem e estrutura permanente.

Ela existe para captacao, normalizacao, roteamento, observabilidade e elasticidade controlada de sinais.

Scaffold Agents podem interagir com ela, mas nao se confundem com ela.

O que eles podem fazer ao lado da malha:

1. monitorar canais ainda instaveis
2. bloquear entrada perigosa durante transicao
3. aplicar observacao temporaria mais agressiva
4. registrar onde a malha ainda precisa ser amadurecida

O que eles nao podem fazer:

1. virar a propria malha
2. engolir os canais permanentes da Signal Mesh

## Funcao real dos Scaffold Agents

Os Scaffold Agents existem para sustentar construcao segura.

Seus papeis permitidos sao:

1. observacao
2. validacao de transicao
3. contencao temporaria
4. telemetria reforcada
5. bloqueio de risco excepcional
6. adaptacao provisoria entre entrada antiga e estrutura nova

Seus papeis proibidos sao:

1. regra de negocio principal
2. orquestracao central definitiva
3. ponto oficial de entrada duradouro
4. substituicao do dominio, da aplicacao ou da malha permanente

## Regras obrigatorias

Todo Scaffold Agent deve ter:

1. nome claro
2. motivo explicito de existencia
3. fluxo ou corredor que ele protege
4. risco que ele esta mitigando
5. criterio de remocao
6. dono tecnico responsavel

Sem isso, ele nao deve existir.

## Criterio de entrada

Um Scaffold Agent so pode nascer se pelo menos uma destas condicoes for verdadeira:

1. existe bypass historico ainda necessario
2. existe migracao arquitetural em andamento
3. existe integracao antiga que nao pode ser desligada ainda
4. existe risco operacional alto durante a troca de rota
5. existe necessidade temporaria de observacao reforcada

## Criterio de remocao

Um Scaffold Agent deve ser removido quando:

1. o corredor oficial correspondente estiver pronto
2. o fluxo ja estiver entrando pelo CENTER ou pela estrutura permanente correta
3. o risco transitivo que justificava sua existencia desaparecer
4. o bypass historico for desligado

Regra dura:

1. agent temporario sem criterio de remocao vira deuda arquitetural ativa

## Riscos reais

### Risco 1: o temporario virar permanente

Sintoma:

1. o agent continua ali por comodidade
2. ninguem mais sabe se ele ainda e necessario

Mitigacao:

1. criterio de remocao obrigatorio
2. revisao periodica dos agents ativos
3. documentacao de data, motivo e destino arquitetural

### Risco 2: o agent virar dono de negocio

Sintoma:

1. logica central vai sendo empurrada para o andaime

Mitigacao:

1. agent so observa, protege, adapta ou bloqueia
2. regra final continua no nucleo permanente

### Risco 3: o agent esconder o problema real

Sintoma:

1. ele impede falha, mas ninguem corrige a causa estrutural

Mitigacao:

1. todo agent precisa apontar explicitamente para o corredor definitivo que deve substitui-lo
2. o agent nao e fechamento do problema; ele e protecao de transicao

### Risco 4: proliferacao de agents

Sintoma:

1. cada fragilidade vira um agent novo
2. a obra fica coberta de andaimes demais

Mitigacao:

1. criar apenas quando o risco e real e a transicao esta ativa
2. preferir remover rapel e consolidar corredor oficial em vez de multiplicar agentes

## Regra arquitetural consolidada

O modelo completo do predio passa a ser este:

1. Nivel 1 = acesso externo
2. Center Layer = hall oficial de entrada
3. Nivel 2 = nucleo interno encaixotado
4. Signal Mesh = malha permanente de sinais, integracoes e elasticidade controlada
5. Rapeis = caminhos excepcionais de transicao
6. Scaffold Agents = operadores temporarios desses caminhos

## Estado correto de maturidade

Sistema imaturo:

1. muitos rapeis
2. muitos Scaffold Agents
3. pouco CENTER consolidado

Sistema em consolidacao:

1. CENTER crescendo
2. Signal Mesh ganhando forma
3. rapéis diminuindo
4. Scaffold Agents sendo removidos

Sistema maduro:

1. CENTER dominante
2. Signal Mesh permanente e controlada
3. nucleo encaixotado protegido
4. poucos ou nenhum Scaffold Agent restante

## Estado atual

Neste momento, os Scaffold Agents sao um conceito oficial de transicao, nao uma camada implementada como mecanismo genérico no codigo.

Isso e o estado correto.

O objetivo agora nao e sair criando agentes por toda parte. O objetivo e nomear corretamente o que e temporario, impedir sua cristalizacao e garantir que a arquitetura final continue limpa.

Acima da obra e das transicoes, a emissao visivel do estado do predio foi formalizada em [red-beacon.md](red-beacon.md).