<!--
ARQUIVO: formalizacao da Signal Mesh como plano diagonal de sinais, integracoes e expansao transversal do sistema.

TIPO DE DOCUMENTO:
- direcao arquitetural satelite

AUTORIDADE:
- alta

DOCUMENTO PAI:
- [octobox-architecture-model.md](octobox-architecture-model.md)

QUANDO USAR:
- quando a duvida for como sinais, integracoes, retries, envelopes e observabilidade devem viver ao redor do core

POR QUE ELE EXISTE:
- transforma a intuicao da estrutura expansiva com antena em regra arquitetural legivel e controlada.
- evita que a ideia vire uma camada generica, mistica ou sem fronteiras tecnicas claras.

O QUE ESTE ARQUIVO FAZ:
1. define o que e a Signal Mesh na arquitetura do OctoBox.
2. separa sua funcao da funcao do Center Layer.
3. enumera riscos reais e as mitigacoes obrigatorias para a operacao.

PONTOS CRITICOS:
- a Signal Mesh nao pode substituir o CENTER nem o dominio.
- se ela concentrar regra demais, vira um atalho perigoso e destrutivo para a arquitetura.
-->

# Signal Mesh

## Tese central

Depois do `Center Layer`, o OctoBox passa a precisar de uma segunda estrutura arquitetural complementar.

Essa nova estrutura nao e um novo andar comum.

Ela e uma malha de expansao transversal, ligada ao CENTER, que pode crescer diagonalmente pela estrutura para:

1. captar sinais externos
2. normalizar entradas tecnicas
3. distribuir eventos e envelopes para os pontos corretos
4. sustentar integracoes, automacoes, webhooks, filas e reprocessamentos

Essa estrutura foi nomeada como `Signal Mesh`.

Em linguagem simples:

1. o CENTER e o hall de entrada
2. a Signal Mesh e a rede de circulacao e antena do predio

## O que a Signal Mesh resolve

Sem essa estrutura, o sistema tende a espalhar integracoes e sinais por varios cantos:

1. webhook em view
2. callback direto em service
3. job com regra parcial duplicada
4. retry improvisado
5. payload externo vazando para o nucleo

O efeito disso e previsivel:

1. acoplamento tecnico se espalha
2. contratos externos contaminam o dominio
3. eventos e automacoes crescem sem forma unica
4. a leitura do sistema piora conforme integra mais coisas

A Signal Mesh existe para impedir isso.

## Elasticidade controlada

A Signal Mesh nao e apenas uma malha transversal.

Ela tambem passa a ser definida como uma estrutura de elasticidade controlada.

Isso significa:

1. a malha tem um tamanho basal fixo
2. a malha pode expandir quando necessario
3. a malha expande apenas dentro de guardrails
4. a malha retrai para o estado basal quando o risco ou a pressao passam
5. a integridade estrutural vale mais do que a ambicao de throughput

Em linguagem simples:

1. o estado normal da malha e estavel
2. a expansao e excepcional, controlada e inteligente
3. quando o crescimento ameaca a estrutura, a malha se contem e volta ao baseline seguro

Nome tecnico recomendado para essa propriedade:

1. `Bounded Elastic Mesh`

## Baseline e expansao

### Baseline

O baseline e o tamanho fixo e seguro da malha.

Ele define:

1. a capacidade normal de operacao
2. os corredores ativos por padrao
3. o comportamento estavel esperado fora de picos e excecoes

Regra:

1. toda implementacao da Signal Mesh deve ter baseline explicito
2. a malha nunca nasce expandida por padrao

### Expansao

A expansao so pode acontecer por necessidade real ou decisao explicita.

Ela pode ser disparada por:

1. pico de trafego
2. fila crescente
3. latencia acima do limite
4. aumento de falhas reprocessaveis
5. janela operacional programada
6. acionamento manual pela operacao

Regra:

1. expansao nao e direito automatico de qualquer canal
2. toda expansao precisa obedecer limites por canal, prioridade e saude estrutural

## Retracao e retorno ao baseline

A Signal Mesh tambem precisa saber voltar.

Essa retracao nao e um detalhe opcional. Ela faz parte da definicao da malha.

A volta ao baseline pode ser disparada por:

1. queda sustentada da carga
2. normalizacao de fila
3. recuperacao de latencia
4. reducao consistente de erro
5. encerramento de janela operacional de pico
6. deteccao de risco estrutural na expansao

Regra:

1. a malha deve preferir voltar ao baseline quando a expansao deixa de ser necessaria
2. a retracao precisa usar histerese, para evitar ficar expandindo e retraindo sem parar

## Autoprotecao estrutural

Na metafora original, a malha "volta ao tamanho original quando algo pode causar dano".

Em termos tecnicos, isso vira a regra de autoprotecao estrutural.

Ela funciona assim:

1. a malha detecta risco estrutural
2. tenta conter localmente o problema
3. degrada de forma controlada quando necessario
4. retrai a elasticidade se o risco continuar
5. preserva o baseline seguro do sistema

Importante:

1. nem todo dano potencial exige retracao imediata de tudo
2. o caminho correto e conter, isolar, degradar e so entao retrair quando for preciso

Ou seja:

1. primeiro isolamento local
2. depois degradacao controlada
3. depois retracao de elasticidade
4. por fim, preservacao do baseline seguro

## Guardrails de elasticidade

Para a elasticidade nao destruir a arquitetura, estes guardrails passam a ser obrigatorios:

1. limite maximo de expansao
2. quota por canal
3. prioridade por tipo de sinal
4. circuit breaker
5. backpressure
6. isolamento por corredor
7. policy de retracao
8. policy de histerese
9. protecao de canais criticos

Resumo da regra:

1. a malha pode crescer
2. a malha nao pode crescer sem freio
3. se crescer ameacando a estrutura, deve se recolher

## Lugar da Signal Mesh no predio

O predio agora passa a ser lido assim:

### Nivel 1: acesso

1. views
2. admin
3. API
4. jobs
5. integracoes de entrada

### CENTER: entrada publica por capacidade

1. organiza a conversa do mundo externo com capacidades do produto
2. expõe entradas publicas pequenas e legiveis

### Nivel 2: nucleo interno

1. `application`
2. `domain`
3. `infrastructure`

### Signal Mesh: malha diagonal de sinais

1. atravessa o predio lateralmente
2. conecta fontes externas, eventos internos e automacoes
3. distribui envelopes tecnicos sem deformar o nucleo

## Diferenca entre CENTER e Signal Mesh

### Center Layer

Serve para:

1. entrada publica oficial por capacidade
2. organizacao da conversa entre acesso e nucleo
3. ocultar wiring interno da borda externa

Pergunta que o CENTER responde:

1. como o mundo externo entra oficialmente nessa capacidade?

### Signal Mesh

Serve para:

1. captacao de sinais
2. normalizacao de envelopes
3. roteamento tecnico
4. integracoes cruzadas
5. automacoes e reprocessamentos

Pergunta que a Signal Mesh responde:

1. como sinais entram, circulam, sao observados e chegam ao destino correto sem contaminar o nucleo?

Resumo:

1. o CENTER e porta oficial
2. a Signal Mesh e malha de propagacao

Os mecanismos temporarios de obra, migracao e suporte a rapeis nao pertencem a nenhuma dessas duas estruturas permanentes. Eles foram formalizados separadamente em [scaffold-agents.md](scaffold-agents.md).

## A "antena"

Na metafora do predio, a Signal Mesh possui uma antena embutida.

Tecnicamente, isso significa que ela tem capacidade explicita de captacao.

Essa captacao pode incluir:

1. webhooks
2. mensagens de WhatsApp
3. callbacks de provedores
4. sinais de fila
5. eventos internos do produto
6. cron jobs e rotinas de monitoramento
7. futuros sinais de app mobile, bots, CRM e integracoes terceiras

Regra obrigatoria:

1. a antena capta e normaliza
2. a antena nao decide o negocio final sozinha

## Camadas internas da Signal Mesh

Para a malha nao virar caos, ela deve ser lida em cinco partes.

### 1. Captacao

Recebe sinais brutos do ambiente.

Exemplos:

1. payload HTTP externo
2. evento interno publicado
3. callback de provedor
4. disparo de job

### 2. Normalizacao

Converte a entrada bruta para um envelope interno estavel.

Esse envelope deve carregar apenas o necessario:

1. origem
2. tipo do sinal
3. payload saneado
4. metadata tecnica
5. idempotency key quando existir

### 3. Roteamento

Decide qual corredor, capacidade ou fluxo deve receber o sinal.

Pode rotear para:

1. facade do CENTER
2. caso de uso especifico
3. fila de reprocessamento
4. mecanismo de observabilidade

### 4. Execucao tecnica

Dispara a entrega do envelope ao destino correto.

Essa camada pode:

1. chamar ports e adapters
2. acionar retries
3. usar fila
4. persistir estado tecnico de entrega

### 5. Observabilidade

Registra o comportamento tecnico da malha.

Exemplos:

1. trace de entrega
2. falhas
3. retries
4. dead letter
5. auditoria tecnica
6. metricas de trafego

### 6. Elasticidade e autoprotecao

Regula o comportamento adaptativo da malha.

Essa camada e responsavel por:

1. medir pressao operacional
2. decidir expansao permitida
3. decidir retracao segura
4. aplicar isolamento, backpressure e circuit breaker
5. proteger o baseline estrutural

## Regras duras da Signal Mesh

Para a ideia funcionar, estas regras deixam de ser opcionais:

1. a Signal Mesh nao substitui o CENTER
2. a Signal Mesh nao substitui `application` ou `domain`
3. payload externo nunca entra cru no nucleo
4. cada sinal precisa ter tipo, origem e envelope claros
5. cada integracao precisa ter contrato e politica de falha
6. retries precisam ser idempotentes ou bloqueados por desenho
7. toda falha relevante precisa ter trilha tecnica observavel
8. toda expansao precisa ter limite maximo e criterio de retracao
9. a malha deve preferir conter e degradar antes de colapsar

## Os riscos reais da operacao

Esta ideia e forte, mas tambem e perigosa se for mal executada.

### Risco 1: a malha virar um lugar onde tudo entra e nada tem dono

Sintoma:

1. modulo gigante
2. nomes vagos
3. qualquer tipo de logica sendo jogada ali

Mitigacao obrigatoria:

1. dividir por captacao, envelopes, roteadores e observabilidade
2. nomear canais e sinais por capacidade real
3. proibir modulos genericos do tipo `utils_de_evento.py` como centro da malha

### Risco 2: a Signal Mesh engolir o dominio

Sintoma:

1. regras centrais decididas no roteador
2. integracao externa determinando politica de negocio

Mitigacao obrigatoria:

1. a malha apenas captura, normaliza e distribui
2. decisao de negocio continua em `domain` e `application`
3. todo roteador deve ser revisado como infraestrutura, nao como dominio

### Risco 3: duplicidade de fluxo com o CENTER

Sintoma:

1. a mesma capacidade passa a ter entrada pelo CENTER e pela malha sem criterio

Mitigacao obrigatoria:

1. o CENTER continua sendo a porta oficial por capacidade
2. a malha alimenta o CENTER ou fluxos internos bem definidos
3. toda nova integracao precisa dizer explicitamente se entra pelo CENTER, pela malha ou por ambos

### Risco 4: explosao de acoplamento tecnico

Sintoma:

1. provedores externos vazando para toda a base
2. callbacks espalhados em varios modulos

Mitigacao obrigatoria:

1. normalizar tudo em envelopes internos pequenos
2. manter adapters concretos isolados na borda tecnica da malha
3. proibir consumo direto de payload externo fora da captacao/normalizacao

### Risco 5: retries destrutivos ou inconsistentes

Sintoma:

1. mensagens duplicadas
2. reprocessamento causando side effect repetido

Mitigacao obrigatoria:

1. usar idempotency key quando houver sinal repetivel
2. diferenciar falha reprocessavel de falha terminal
3. prever fila de erro e politica de dead letter

### Risco 6: observabilidade insuficiente

Sintoma:

1. nao se sabe onde um sinal morreu
2. integracao falha em silencio

Mitigacao obrigatoria:

1. todo canal importante deve emitir trilha tecnica
2. falhas precisam carregar origem, tipo de sinal e correlacao
3. eventos silenciosos devem ser excecao documentada, nao padrao

### Risco 7: crescimento sem divisorias claras

Sintoma:

1. a malha cresce e vira monolito transversal

Mitigacao obrigatoria:

1. separar por canais e envelopes
2. crescer por divisorias reais
3. tratar cada nova capacidade como corredor ou canal proprio

### Risco 8: elasticidade agressiva demais

Sintoma:

1. a malha expande demais
2. a malha consome estrutura alem do necessario
3. um pico local contamina o sistema todo

Mitigacao obrigatoria:

1. baseline explicito
2. quota por canal
3. limite maximo de expansao
4. isolamento por corredor
5. circuit breaker e backpressure

### Risco 9: retracao cega causando perda de estabilidade funcional

Sintoma:

1. a malha recolhe tudo cedo demais
2. canais criticos sao prejudicados junto com canais secundarios

Mitigacao obrigatoria:

1. retracao com histerese
2. degradacao local antes de retracao global
3. preservacao explicita de canais criticos
4. retorno ao baseline seguro, nao ao silencio total

## O que e permitido dentro da Signal Mesh

1. adapters de captura
2. envelopes internos
3. roteadores tecnicos
4. observabilidade
5. retries, fila e reprocessamento
6. mascaramento de payload sensivel
7. saneamento e validacao estrutural de entrada
8. politicas de elasticidade, contencao e retracao

## O que e proibido dentro da Signal Mesh

1. regra de negocio central do produto
2. heuristica comercial ou operacional principal
3. logica de tela
4. renderizacao HTTP
5. dependencia direta do payload externo no dominio
6. repositorio generico que sabe tudo sobre todos os canais

## Forma de crescimento

Esta estrutura foi pensada para crescer quase sem limite, mas com disciplina.

Ela cresce por:

1. canais
2. envelopes
3. roteadores
4. observabilidade
5. conectores
6. elasticidade bounded com baseline claro

Ela nao cresce por:

1. modulo unico centralizador
2. acumulacao caotica de ifs por integracao
3. expansao infinita sem guardrail

## Como essa estrutura entra no primeiro terco do projeto

No primeiro terco, a prioridade ainda nao e construir a malha inteira.

A prioridade e:

1. formalizar o conceito
2. impedir implementacao errada futura
3. posicionar a malha ao lado do CENTER sem confundir funcoes

Ou seja:

1. o CENTER organiza entrada publica
2. a Signal Mesh organiza sinais e expansao transversal
3. os dois convivem, mas com papeis diferentes

## Estado atual

Hoje a Signal Mesh ainda e um conceito arquitetural formalizado, nao uma camada implementada em larga escala.

Isso e correto para esta fase.

O erro agora seria codar uma malha gigante antes de fixar seus limites. O acerto e fazer o que este documento estabelece:

1. nome oficial
2. funcao oficial
3. fronteira oficial
4. riscos conhecidos
5. mitigacoes obrigatorias
6. baseline estrutural
7. regras de expansao e retracao

Quando a hora de implementacao chegar, a malha ja tera desenho claro suficiente para crescer sem destruir o predio.

Acima dela, a camada responsavel por projetar estado consolidado para fora foi formalizada em [red-beacon.md](red-beacon.md).