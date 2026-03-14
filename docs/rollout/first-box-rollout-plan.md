<!--
ARQUIVO: plano pratico para colocar o OctoBox em uso nos primeiros boxes com risco controlado.

TIPO DE DOCUMENTO:
- execucao ativa de rollout

AUTORIDADE:
- alta

DOCUMENTO PAI:
- [../architecture/architecture-growth-plan.md](../architecture/architecture-growth-plan.md)

QUANDO USAR:
- quando a duvida for como abrir operacao real de campo em ondas pequenas e com risco controlado

POR QUE ELE EXISTE:
- muda o foco do projeto de construcao interna para operacao real com clientes iniciais.
- organiza infraestrutura, onboarding, suporte e criterio de rollout em uma mesma trilha.

O QUE ESTE ARQUIVO FAZ:
1. define o pacote minimo para abrir o sistema para boxes reais.
2. organiza a entrada dos primeiros clientes em ondas pequenas.
3. registra criterio de pronto, risco e prioridade de execucao.

PONTOS CRITICOS:
- abrir cedo demais sem trilha de suporte vira desgaste de produto.
- tentar abrir para muitos boxes de uma vez aumenta risco sem necessidade.
-->

# Plano de rollout para os primeiros boxes

## Objetivo

Colocar o OctoBox para rodar com os primeiros boxes em um formato controlado, simples e suficientemente seguro para uso real.

Meta inicial:

1. sair de ambiente interno
2. publicar um ambiente estavel
3. operar com poucos boxes piloto
4. aprender rapido com uso real sem quebrar confianca

## Regra central

Nao vamos tentar escalar agora.

Vamos abrir uma operacao pequena, assistida e disciplinada.

Em linguagem simples:

1. primeiro provar uso real
2. depois estabilizar suporte e onboarding
3. so depois ampliar

## O que ja existe hoje

O projeto ja tem um pacote tecnico minimo importante:

1. settings de producao com PostgreSQL e WhiteNoise em [config/settings/production.py](../../config/settings/production.py)
2. base de ambiente em [config/settings/base.py](../../config/settings/base.py)
3. guia de deploy em [deploy-homologation.md](deploy-homologation.md)
4. checklist exato de homologacao em [homologation-deploy-checklist.md](homologation-deploy-checklist.md)
4. guia de backup em [backup-guide.md](backup-guide.md)
5. dependencias minimas de producao em [requirements.txt](../../requirements.txt)

Conclusao:

1. nao estamos saindo do zero para publicar
2. o proximo passo e empacotar isso como operacao real de campo

## Estrutura da entrada em campo

### Fase 1: pacote minimo de producao

Objetivo:

1. ter um ambiente publico estavel o suficiente para uso piloto

Entregas:

1. hospedagem definida
2. PostgreSQL configurado
3. dominio ou subdominio configurado
4. HTTPS funcionando
5. collectstatic no fluxo de deploy
6. backup automatico diario
7. superuser e bootstrap de papeis executados

Criterio de pronto:

1. o sistema sobe fora da maquina local
2. login funciona
3. assets carregam corretamente
4. backup existe e foi testado

### Fase 2: pacote minimo de operacao do box

Objetivo:

1. definir o que o primeiro box realmente vai usar sem confusao

Escopo inicial recomendado:

1. login e papeis
2. dashboard
3. alunos
4. cadastro e edicao leve
5. cobranca curta
6. grade de aulas em leitura
7. Recepcao

O que nao precisa entrar no piloto como promessa central:

1. uso amplo do admin
2. complexidade comercial avancada demais
3. operacao muito customizada por box
4. integracoes pesadas antes da rotina basica ficar viva

Criterio de pronto:

1. um box consegue operar rotina basica diaria sem depender do admin para tudo

### Fase 3: onboarding assistido do primeiro box

Objetivo:

1. fazer a primeira implantacao como acompanhamento proximo, nao como software solto

Checklist:

1. criar usuarios e papeis do box
2. cadastrar planos principais
3. importar ou cadastrar base inicial de alunos
4. configurar grade essencial
5. testar fluxo real de atendimento, cadastro e pagamento
6. explicar a fronteira entre Recepcao, Manager e Coach

Criterio de pronto:

1. o box consegue rodar um dia real de operacao com ajuda leve, nao com socorro constante

### Fase 4: suporte de campo dos primeiros 7 a 14 dias

Objetivo:

1. capturar atrito real e corrigir rapido antes de abrir mais boxes

Checklist:

1. canal unico para feedback e bug
2. rotina diaria curta de triagem
3. classificacao de problema por severidade
4. pequenas correcoes com deploy rapido
5. registro do que confunde, trava ou gera retrabalho

Criterio de pronto:

1. os problemas recorrentes diminuem e o uso comeca a ganhar ritmo proprio

### Fase 5: segunda onda de boxes piloto

Objetivo:

1. validar que o aprendizado do primeiro box se sustenta em outros contextos

Recomendacao:

1. nao abrir para muitos de uma vez
2. entrar em 2 ou 3 boxes no maximo na segunda onda

Criterio de pronto:

1. o onboarding ja esta mais simples
2. os bugs graves mais previsiveis ja foram contidos
3. o produto ja nao depende de intervencao artesanal em tudo

## Prioridades imediatas

### Prioridade 1: publicar homologacao real

Fazer agora:

1. escolher plataforma de deploy
2. subir ambiente com `DJANGO_ENV=production`
3. apontar banco PostgreSQL
4. configurar variaveis sensiveis
5. validar login, static files e rotas principais

### Prioridade 2: definir pacote do piloto

Fazer agora:

1. congelar o escopo inicial do box piloto
2. declarar o que entra e o que fica fora da primeira venda
3. preparar script de onboarding minimo em [first-box-onboarding-runbook.md](first-box-onboarding-runbook.md)

### Prioridade 3: preparar suporte operacional

Fazer agora:

1. definir como bugs serao recebidos
2. definir tempo esperado de resposta
3. definir criterio de severidade
4. definir rotina de backup e restauracao
5. registrar o fluxo de triagem em [pilot-support-playbook.md](pilot-support-playbook.md)

### Prioridade 4: abrir o primeiro box com acompanhamento proximo

Fazer agora:

1. escolher o primeiro box certo
2. nao escolher o mais complexo
3. escolher um cliente que aceite colaborar com feedback rapido

## O primeiro box ideal

Caracteristicas desejadas:

1. operacao pequena ou media
2. dono acessivel
3. disposicao para testar e responder rapido
4. rotina relativamente simples
5. abertura para corrigir processo junto com o produto

Evitar agora:

1. box com operacao muito caotica
2. cliente que exige personalizacao pesada logo no inicio
3. ambiente sem disciplina minima de uso

## Riscos principais

### Risco 1: abrir com escopo grande demais

Mitigacao:

1. vender piloto assistido
2. limitar capacidade inicial prometida

### Risco 2: publicar sem trilha de backup e suporte

Mitigacao:

1. backup automatico antes de abrir
2. canal claro de suporte desde o primeiro dia

### Risco 3: usar o primeiro box como palco de refatoracao

Mitigacao:

1. durante o piloto, priorizar estabilidade e clareza
2. refatoracao estrutural so quando reduzir risco real de operacao

## Sequencia recomendada dos proximos passos

1. subir homologacao publica real
2. validar pacote tecnico minimo
3. definir escopo fechado do piloto
4. preparar onboarding do primeiro box com [first-box-onboarding-runbook.md](first-box-onboarding-runbook.md)
5. colocar o primeiro box para rodar
6. acompanhar 7 a 14 dias com [pilot-support-playbook.md](pilot-support-playbook.md)
7. corrigir atritos graves
8. abrir segunda onda pequena

## Formula pratica

O proximo passo do projeto nao e buscar perfeicao interna.

O proximo passo e construir uma operacao pequena, confiavel e repetivel para os primeiros boxes.

Em linguagem curta:

1. publicar
2. pilotar
3. estabilizar
4. repetir