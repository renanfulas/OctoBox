<!--
ARQUIVO: playbook de suporte dos primeiros boxes piloto.

TIPO DE DOCUMENTO:
- playbook operacional de suporte

AUTORIDADE:
- alta para a fase piloto assistida

DOCUMENTO PAI:
- [first-box-rollout-plan.md](first-box-rollout-plan.md)

QUANDO USAR:
- quando a duvida for como receber bugs, classificar severidade e responder no piloto sem caos operacional

POR QUE ELE EXISTE:
- impede que o suporte do piloto vire troca de mensagens soltas sem triagem e sem criterio.
- cria uma rotina minima para aprender com o uso real sem desgastar a confianca do box.

O QUE ESTE ARQUIVO FAZ:
1. define canal e formato de entrada dos chamados.
2. organiza severidade, resposta e escalonamento.
3. registra a rotina curta dos primeiros 7 a 14 dias.

PONTOS CRITICOS:
- este playbook serve para o piloto assistido, nao para suporte em escala.
- todo ajuste em producao precisa respeitar backup e rastreabilidade minima.
-->

# Playbook de suporte do piloto

## Objetivo

Operar os primeiros boxes piloto com uma rotina curta de suporte, triagem e correção, sem transformar cada bug em improviso isolado.

## Canal unico do piloto

Definir um unico canal de entrada por box piloto.

Opcoes validas:

1. WhatsApp dedicado
2. grupo curto com responsavel do box
3. email unico do piloto
4. board simples de chamados

Nao operar com multiplos canais paralelos.

## Formato minimo de cada chamado

Toda duvida ou bug precisa entrar com:

1. papel da pessoa que sofreu o problema
2. tela ou rota onde aconteceu
3. o que ela tentou fazer
4. o que aconteceu de errado
5. print ou video curto quando possivel

## Severidade

### Severidade 1. Bloqueio total

Exemplos:

1. login nao funciona
2. dashboard nao abre
3. erro 500 em tela central
4. pagamento curto nao salva

Resposta esperada:

1. triagem imediata
2. correcao ou contencao no mesmo dia

### Severidade 2. Fluxo degradado

Exemplos:

1. tela abre, mas com dado errado
2. busca falha em parte dos casos
3. copy confunde a operacao
4. um papel consegue entrar, mas a jornada trava no meio

Resposta esperada:

1. triagem no mesmo dia
2. correcao em janela curta priorizada

### Severidade 3. Ajuste de conforto ou refinamento

Exemplos:

1. melhoria de copy
2. ajuste visual
3. campo que poderia orientar melhor
4. refinamento de leitura operacional

Resposta esperada:

1. registrar no backlog
2. agrupar com outros ajustes do piloto

## Rotina diaria do piloto

Durante os primeiros 7 a 14 dias:

1. abrir uma triagem curta no inicio do dia
2. revisar novos chamados
3. classificar severidade
4. separar o que corrige agora e o que entra em backlog
5. fechar o dia com resumo simples do que foi tratado

## Regra para deploy de correcoes

Antes de subir ajuste em ambiente piloto:

1. confirmar o problema com reproducao minima
2. validar se o ajuste toca fluxo critico
3. garantir backup recente do banco quando a correcao afetar dado ou migracao
4. registrar o hash ou versao liberada apos o deploy

## Informacoes que nao podem faltar na triagem

Ao registrar um problema do piloto, anotar:

1. box afetado
2. usuario afetado
3. papel afetado
4. tela afetada
5. severidade
6. status do tratamento

## Perguntas boas na primeira resposta

1. qual papel do usuario?
2. qual tela exatamente?
3. isso aconteceu uma vez ou sempre?
4. o problema impede operar ou so atrasa?
5. ha workaround temporario?

## O que nao fazer no piloto

1. aceitar pedido de customizacao grande como se fosse bug
2. misturar suporte com reescrita estrutural
3. fazer deploy sem saber o que esta corrigindo
4. deixar severidade alta competir com polimento visual pequeno

## Saidas esperadas do piloto

Ao fim dos primeiros 7 a 14 dias, precisamos ter:

1. lista dos bugs severos reais
2. lista do que mais confundiu a operacao
3. lista do que o box mais usou
4. backlog limpo para a segunda onda

## Formula curta

No piloto, suporte bom nao e responder tudo na hora.

Suporte bom e separar rapido o que bloqueia, corrigir com criterio e aprender com cada atrito.