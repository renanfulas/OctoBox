<!--
ARQUIVO: arquitetura de acesso profundo controlado para operacoes sensiveis.

TIPO DE DOCUMENTO:
- arquitetura de capacidade e seguranca operacional

AUTORIDADE:
- alta para acesso profundo, admin sensivel e elevacao temporaria

DOCUMENTO PAI:
- [octobox-architecture-model.md](octobox-architecture-model.md)

QUANDO USAR:
- quando a duvida for como separar operacao normal de operacao profunda
- quando a pergunta for como proteger owner e dev contra credencial roubada sem travar o uso normal
- quando for necessario decidir o papel do Django admin, da auditoria e das liberacoes temporarias

POR QUE ELE EXISTE:
- evita tratar o admin como corredor cotidiano e cofre ao mesmo tempo
- substitui a resposta binaria de honeypot automatico por uma fronteira operacional mais elegante
- cria um modelo de contencao que protege o negocio sem punir o uso normal

O QUE ESTE ARQUIVO FAZ:
1. define a tese de acesso em camadas com elevacao temporaria
2. separa zona normal, zona elevada e zona profunda
3. formaliza liberacao temporaria, escopo, expiracao e revogacao
4. posiciona honeypot como resposta excepcional, nao como primeira reacao

PONTOS CRITICOS:
- essa arquitetura nao substitui MFA, rate limit, edge security e auditoria
- acesso profundo nao pode depender apenas de senha primaria
- liberacao manual sem trilha, escopo e expiracao vira novo ponto cego
-->

# Arquitetura de acesso profundo controlado

## Regra de autoridade deste documento

1. este documento define a tese estrutural para acesso profundo e administracao sensivel
2. o plano de execucao traduz a ordem pratica, mas nao altera sozinho a fronteira conceitual
3. docs de seguranca de edge e baseline continuam valendo para rate limit, proxy e blocklist

## Tese central

O OctoBox deixa de tratar o Django admin como corredor cotidiano.

Ele passa a tratar o admin como cofre frio.

Em linguagem direta:

1. uso normal do produto deve acontecer em superficies proprias do produto
2. uso sensivel recorrente deve sair do admin e ganhar paginas dedicadas
3. uso profundo, raro ou extraordinario deve exigir elevacao temporaria
4. owner e dev continuam poderosos, mas nao ficam com o cofre destrancado o dia inteiro

Metafora simples:

1. a recepcao do predio fica aberta para quem trabalha la
2. a sala do cofre continua trancada
3. quando alguem precisa entrar no cofre, pede autorizacao, explica o motivo e recebe uma chave que expira

## Problema que esta arquitetura resolve

O modelo antigo deixava tres riscos misturados:

1. o admin era ao mesmo tempo ferramenta de rotina e area sensivel
2. um comportamento suspeito podia disparar contenção brusca demais
3. uma credencial roubada de owner ou dev herdava profundidade demais por tempo demais

Essa mistura e perigosa porque transforma o sistema em uma casa onde a chave-mestra abre desde a portaria ate a sala do cofre sem segunda barreira.

## Modelo proposto

O nome oficial desta capacidade passa a ser:

1. Acesso em Camadas com Elevacao Temporaria

Esse modelo separa o produto em tres zonas.

### Zona 1: acesso normal

Aqui fica o uso cotidiano, operacional e fluido.

Exemplos:

1. dashboard
2. alunos
3. cobranca comum
4. operacao por papel
5. acoes recorrentes que podem e devem ter UX propria

Regra:

1. a pessoa trabalha normalmente
2. o fluxo nao depende do admin
3. a autenticação primaria e os controles normais sustentam essa camada

### Zona 2: acesso elevado

Aqui ficam operacoes sensiveis, mas legitimamente recorrentes.

Exemplos:

1. troca de plano
2. mudanca comercial com impacto financeiro relevante
3. acoes operacionais de maior risco que ainda pertencem ao produto de frente

Regra:

1. essas acoes devem ganhar paginas proprias
2. a pessoa pode precisar de reautenticacao
3. a sessao pode precisar de confianca alta
4. o sistema deve registrar a intencao e o contexto

### Zona 3: acesso profundo

Aqui fica a retaguarda rara e sensivel.

Exemplos:

1. Django admin puro
2. auditoria profunda
3. alteracao de configuracao estrutural
4. manutencao rara de objetos internos
5. inspecao detalhada de areas que nao pertencem ao fluxo normal do produto

Regra:

1. acesso bloqueado por padrao
2. acesso depende de elevacao temporaria
3. acesso deve ser escopado, auditado e reversivel

## Regra-mestra de design

Tudo que for recorrente e legitimo deve sair do admin.

Tudo que for raro e perigoso deve continuar fora do fluxo normal.

Traducao pratica:

1. o admin nao e a UX do negocio
2. o admin e a reserva tecnica do predio
3. o produto deve absorver as operacoes que sao normais demais para continuar escondidas no backoffice

## Componentes centrais da arquitetura

### 1. Deep Access Request

Representa o pedido de elevacao.

Campos minimos esperados:

1. usuario
2. papel atual
3. motivo informado
4. escopo pedido
5. sessao
6. IP
7. user agent
8. horario

### 2. Deep Access Grant

Representa a liberacao temporaria.

Campos minimos esperados:

1. quem pediu
2. quem liberou
3. quando comecou
4. quando expira
5. escopo concedido
6. justificativa
7. vinculo com sessao, dispositivo ou IP quando fizer sentido
8. status da concessao

### 3. Grant Scope

Escopo e a parte mais importante da seguranca elegante.

Nao liberar o predio inteiro se a pessoa so precisa de uma sala.

Escopos candidatos:

1. `plan_management`
2. `finance_admin_read`
3. `finance_admin_write`
4. `audit_read`
5. `user_access_admin`
6. `full_admin_break_glass`

### 4. Grant Expiration

A elevacao precisa morrer sozinha.

Janelas sugeridas:

1. 24h para necessidade comum extraordinaria
2. 48h apenas quando houver justificativa operacional real
3. expiracao imediata apos incidente concluido quando o trabalho for pontual

### 5. Session Trust

Papel e confianca nao sao a mesma coisa.

O usuario pode ser owner e a sessao estar:

1. alta confianca
2. media confianca
3. baixa confianca
4. em contencao

Regra:

1. a permissao estrutural do usuario continua existindo
2. a profundidade efetiva da sessao depende da confianca atual

### 6. Security Event

Cada pedido, tentativa bloqueada, concessao, expiracao e revogacao precisa virar evento auditavel.

Isso evita o fantasma operacional de "o sistema mudou de ideia sozinho".

### 7. Out-of-band Validation

Para owner e dev, a confirmacao humana fora da sessao digital vira parte oficial do desenho.

Exemplos:

1. ligacao
2. contato validado previamente
3. challenge externo

Motivo:

1. o atacante pode roubar senha
2. o atacante pode nao conseguir passar na confirmacao humana real

## Papel do honeypot neste modelo

O honeypot nao desaparece.

Ele muda de lugar.

Regra nova:

1. honeypot continua util para scanner, IP malicioso e insistencia claramente hostil
2. honeypot deixa de ser primeira resposta para navegacao profunda de usuario autenticado
3. honeypot passa a ser resposta excepcional depois de bloqueio, score alto e sinais compostos

Em linguagem simples:

1. primeiro vem a porta travada
2. depois vem o seguranca
3. so no ultimo caso vem a sala falsa

## O que esta arquitetura exige do produto

### 1. Migrar operacoes recorrentes para superficies proprias

Operacoes candidatas:

1. troca de plano
2. ajustes comerciais frequentes
3. algumas mudancas financeiras de rotina
4. leitura operacional de auditoria amigavel

Regra:

1. se a operacao e recorrente, o produto deve assumi-la
2. se a operacao continua escondida no admin por comodidade, a superficie de risco fica errada

### 2. Tratar admin como cofre frio

O admin precisa deixar de ser caminho normal de exploracao.

Isso significa:

1. menos links naturais para o admin
2. mais bloqueio explicito para acesso profundo sem grant
3. mais consciencia de que entrar ali ja e um evento extraordinario

### 3. Declarar politicas por escopo, nao por improviso

Regras de acesso profundo nao podem ficar espalhadas em ifs narrativos.

O sistema precisa saber:

1. qual recurso pede grant
2. qual escopo libera esse recurso
3. qual papel pode pedir
4. quem pode conceder
5. como expira
6. como revoga

## Fluxo oficial

### Fluxo normal

1. usuario acessa superficie comum
2. sistema permite fluxo padrao
3. auditoria registra apenas o que for relevante

### Fluxo de acesso profundo sem grant

1. usuario tenta abrir area profunda
2. sistema bloqueia de forma clara
3. sistema registra evento extraordinario
4. sistema orienta a solicitar liberacao
5. time valida o contexto fora da banda

### Fluxo de acesso profundo com grant

1. usuario recebe grant temporario
2. sistema verifica escopo, expiracao e contexto da sessao
3. usuario acessa somente o que foi liberado
4. eventos ficam auditados
5. grant expira ou e revogado

## Barreiras obrigatorias que nao podem ser esquecidas

### 1. Break-glass controlado

O sistema precisa ter um modo de emergencia raro para restaurar acesso quando:

1. a pessoa certa precisa agir urgente
2. o mecanismo normal de liberacao falhou
3. a crise nao permite esperar o fluxo completo

Mas esse modo precisa ser:

1. auditado
2. raro
3. com TTL curto
4. revisado depois do uso

### 2. Revogacao imediata

Conceder acesso sem conseguir revogar rapido e como emprestar a chave do carro sem ter como desligar o motor.

O sistema precisa permitir:

1. revogar por usuario
2. revogar por sessao
3. revogar por escopo
4. revogar por incidente

### 3. Vinculo contextual da concessao

Sempre que viavel, o grant nao deve viver solto.

Ele deve poder se prender a:

1. sessao
2. IP
3. device fingerprint pragmatico
4. janela de tempo

### 4. Reautenticacao e MFA

Senha primaria sozinha nao deve ser a chave do cofre.

Para acesso elevado e profundo, a arquitetura deve prever:

1. reautenticacao
2. MFA para owner e dev
3. challenge adicional para acoes criticas

### 5. Alertas internos

Se alguem pediu ou tentou acesso profundo, o sistema deve avisar o time certo.

No minimo:

1. evento auditado
2. alerta operacional
3. contexto suficiente para revisao

### 6. UX clara

O sistema nao deve parecer arbitrario.

A mensagem correta e algo como:

1. esta area exige autorizacao temporaria
2. seu acesso padrao cobre a operacao normal
3. para avancar, solicite liberacao extraordinaria

## O que essa arquitetura deliberadamente nao faz

1. nao substitui WAF, edge, rate limit e blocklist
2. nao tenta esconder toda a existencia do admin
3. nao trata qualquer curiosidade como ataque
4. nao rebaixa permanentemente owner ou dev por heuristica isolada

## Riscos se esse desenho for mal implementado

1. depender demais de liberacao manual pode virar gargalo operacional
2. escopos largos demais transformam a protecao em teatro
3. grants sem expiracao automatica viram permissao eterna disfarcada
4. falta de pagina propria para operacao recorrente faz o admin continuar inchado
5. auditoria fraca faz o sistema parecer magico e injusto

## Tese final

O diferencial do OctoBox aqui nao e apenas bloquear mais.

E bloquear melhor.

Em vez de tratar o financeiro e a retaguarda como um corredor aberto ou uma armadilha invisivel, o sistema passa a agir como um banco bem desenhado:

1. o salao principal funciona com fluidez
2. a antecamara filtra o acesso extraordinario
3. o cofre so abre com chave temporaria, contexto validado e trilha completa
