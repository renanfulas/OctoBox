<!--
ARQUIVO: C.O.R.D.A. operacional da arquitetura de acesso do aluno com invite, membership e switch box.

TIPO DE DOCUMENTO:
- prompt operacional reutilizavel
- plano de execucao de produto + backend + UX

AUTORIDADE:
- alta para a trilha de acesso do aluno

DOCUMENTOS PAIS:
- [../architecture/octobox-mobile-architecture.md](../architecture/octobox-mobile-architecture.md)
- [octobox-mobile-execution-plan.md](octobox-mobile-execution-plan.md)
- [../experience/octobox-mobile-guide.md](../experience/octobox-mobile-guide.md)

QUANDO USAR:
- quando a tarefa envolver login do aluno, invite, vinculacao com box, troca de box ou separacao entre aluno e funcionario
- quando precisarmos saber o que ja existe no runtime e o que ainda pertence a proxima fase
- quando quisermos orientar implementacao sem misturar autenticacao, contexto de box e governanca operacional

POR QUE ELE EXISTE:
- evita que a arquitetura do aluno vire conversa solta sem trilho de execucao.
- registra a fotografia atual do runtime e a estrada oficial de evolucao.
- transforma decisoes de produto em backlog tecnico e criterio de pronto.

O QUE ESTE ARQUIVO FAZ:
1. consolida o contrato de entrada do aluno e a separacao entre aluno e funcionario.
2. registra o que ja esta implementado no runtime em 2026-04-16.
3. define a arquitetura-alvo de invite, membership, primary_box, active_box e switch box.
4. ordena a implementacao em fases pequenas, baratas e sem acoplamento indevido.

PONTOS CRITICOS:
- auth social nao deve decidir box por busca global.
- invite contextualiza box; login social prova identidade.
- switch box troca contexto; nao cria vinculo novo.
- inadimplencia suspende acesso; nao apaga identidade.
- login do funcionario nao deve herdar a logica social do aluno.
-->

# C.O.R.D.A. - Acesso do aluno, invite e switch box

## C - Contexto

O OctoBox ja possui duas superficies diferentes:

1. `staff`, com login interno por `username + password`
2. `aluno`, com `student_app` e `student_identity`

O runtime atual ja tem uma base importante pronta:

1. rota de login do aluno em `/aluno/auth/login/`
2. inicio e callback OAuth do aluno para `Google` e `Apple`
3. landing de invite do aluno por token
4. cookie de sessao proprio do aluno
5. PWA do aluno com `manifest`, `sw.js` e shell mobile
6. modelo `StudentIdentity` separado da conta de funcionario
7. modelo `StudentAppInvitation`
8. modelo `StudentTransfer`
9. regra atual de identidade social ancorada em `provider_subject`
10. fluxo atual fortemente ancorado em `single-box`

Em linguagem simples:

1. a casa do aluno ja existe
2. a porta social ja abre
3. o convite ja existe
4. o que falta agora e transformar isso em um predio com corredores melhores, sem derrubar a base pronta

### Fotografia do runtime em 2026-04-17

#### Ja implementado

1. `student_identity.urls` expoe:
   - `login/`
   - `logout/`
   - `invite/<uuid:token>/`
   - `oauth/<provider>/start/`
   - `oauth/<provider>/callback/`
2. `StudentSignInView` ja entrega:
   - `Google`
   - `Apple`
   - `invite_token`
3. `StudentOAuthCallbackView` ja:
   - valida `state`
   - troca `code`
   - resolve identidade
   - emite cookie proprio do aluno
4. `StudentIdentity` hoje tem:
   - `student`
   - `box_root_slug`
   - `provider`
   - `provider_subject`
   - `email`
   - `status`
5. `StudentAppInvitation` hoje tem:
   - `token`
   - `student`
   - `box_root_slug`
   - `invited_email`
   - `expires_at`
   - `accepted_at`
6. existe `StudentTransfer` para migracao de identidade entre boxes
7. o login do staff segue em `access` com `ThrottledLoginView`
8. `/login/` ja funciona como hub publico com separacao visual aluno x funcionario
9. `/login/funcionario/` ja responde com o login interno da equipe
10. `StudentBoxMembership` ja modela vinculo por box com estados formais
11. `StudentIdentity` ja carrega `primary_box_root_slug`
12. o cookie do aluno ja carrega `active_box_root_slug`
13. a topbar do app do aluno ja mostra box atual e `Trocar box`
14. `/aluno/box/switch/` ja troca o contexto ativo sem relogar
15. existe estado `aguardando aprovacao` no app do aluno
16. `StudentAppInvitation` ja diferencia `invite_type`
17. a operacao do box ja consegue aprovar membership pendente

#### Ainda nao implementado

1. throttle separado e afinado por superficie publica (`invite landing`, `callback social`, `aceite`)
2. alertas de anomalia mais ricos por ator, IP e box
3. endurecimento antifraude complementar para device/session risk scoring, se a escala pedir

## O - Objetivo

Implementar a proxima fase da experiencia de acesso do aluno e do hub de entrada do OctoBox com:

1. separacao clara entre `Aluno` e `Funcionario`
2. invite como contexto oficial do box
3. membership explicito entre aluno e box
4. `primary_box` como casa-base do aluno
5. `active_box` como contexto atual de uso
6. `switch box` como troca de contexto, nao de identidade
7. governanca suficiente para evitar fraude, confusao operacional e busca global custosa

Sucesso significa:

1. o aluno entra pelo fluxo social sem o backend precisar procurar em 500 boxes
2. o funcionario continua entrando pelo fluxo atual
3. o aluno pode ter mais de um vinculo com box sem bagunca de sessao
4. o app sabe em qual box operar em toda request relevante
5. o plano continua barato de implementar porque reutiliza a base pronta

## R - Riscos

### 1. Risco de auth social decidir box

Se o sistema continuar tentando descobrir box por email ou heuristica:

1. a autenticacao vira adivinhacao
2. o custo de lookup sobe
3. o comportamento fica confuso em escala

### 2. Risco de duplicidade de identidade

Se email e provedor forem tratados sem contrato:

1. a mesma pessoa pode virar duas identidades
2. suporte e auditoria ficam frouxos

### 3. Risco de switch box virar gambiarra

Se o switch criar vinculo, procurar box ou reautenticar sempre:

1. o fluxo fica pesado
2. o contrato perde clareza
3. a UX vira atrito

### 4. Risco de operacao apagar o que deveria suspender

Se inadimplencia ou falta de uso virarem exclusao:

1. perde-se historico
2. complica-se reativacao
3. mistura-se antifraude com limpeza operacional

### 5. Risco de herdar a logica do aluno para o staff

Se o futuro login social do staff reaproveitar a logica do aluno:

1. a fronteira entre papeis fica errada
2. cresce a chance de acoplamento ruim

## D - Direcao

### Tese central

O fluxo do aluno deve obedecer esta ordem:

1. `auth social` prova quem a pessoa e
2. `invite` define em qual box ela esta entrando
3. `membership` define em quais boxes ela pode operar
4. `primary_box` define a casa-base
5. `active_box` define onde ela esta agora
6. `switch box` troca apenas o contexto atual

### Frases de arquitetura

1. `Invite decide contexto; OAuth decide identidade.`
2. `Membership e vinculo explicito, nao inferencia.`
3. `Switch box troca contexto, nao cria acesso.`
4. `Inadimplencia suspende acesso; nao apaga identidade.`
5. `Aluno e funcionario compartilham fachada de entrada, nao o mesmo corredor interno.`

### Fachada alvo

#### `/login/`

Nova tela-hub com duas portas:

1. `Entrar como aluno`
   - `Continuar com Google`
   - `Continuar com Apple`
2. `Entrar como funcionario`
   - CTA para `/login/funcionario/`

#### `/login/funcionario/`

Recebe a tela atual de `username + password`, com dica para favorito.

### Arquitetura-alvo do aluno

#### Identity

Representa a pessoa.

#### SocialIdentity

Representa a credencial social utilizada.

#### Membership

Representa o vinculo com um box.

#### Primary Box

Representa o box padrao/preferido de entrada.

#### Active Box

Representa o box em uso na sessao atual.

### Politica de centralizacao da identidade

1. a identidade do aluno deve ser tratada como `camada central logica`
2. essa centralizacao deve nascer primeiro na arquitetura atual, nao em um banco fisico separado
3. o objetivo e impedir busca global em todos os boxes a cada novo login ou troca de aparelho
4. o runtime deve resolver:
   - `provider_subject` ou credencial social
   - `StudentIdentity`
   - `StudentBoxMembership`
   - `box_id`

### Regra de infraestrutura

1. nesta fase, `nao` criar um banco separado so para credenciais do aluno
2. primeiro consolidar:
   - `StudentIdentity`
   - `SocialIdentity`
   - `StudentBoxMembership`
   - indices de busca seguros
3. avaliar banco ou servico separado apenas quando houver escala real e maturidade operacional para sustentar mais um ponto de falha

### Motivo

Separar o banco cedo demais parece elegante no papel, mas tende a criar:

1. mais complexidade de deploy
2. mais custo operacional
3. mais sincronizacao entre fontes
4. mais risco presente sem ganho proporcional imediato

Em linguagem simples:

1. primeiro montamos uma portaria central boa dentro do predio atual
2. so depois, se o predio crescer muito, pensamos em construir um predio separado so para a portaria

### Politica de identidade

1. existe `1 email canonico`
2. existe `1 autenticador principal`
3. opcionalmente existe `1 autenticador secundario`
4. troca de email e operacao administrativa e auditavel

### Politica de troca de email

1. `Recepcionista` pode trocar email `1x por aluno por mes`
2. `2a troca no mesmo mes` exige aprovacao de `manager` ou `owner`
3. toda troca registra:
   - `actor`
   - `role`
   - `old_email`
   - `new_email`
   - `reason`
   - `approved_by`
   - `timestamp`

### Politica de invite

#### Tipo 1. Invite aberto do box

1. pode ser compartilhado
2. contextualiza o box
3. gera pedido de membership
4. passa por aprovacao
5. deve ter observabilidade e limite operacional

#### Tipo 2. Invite individual

1. direcionado
2. mais seguro
3. apropriado para casos especificos

### Politica de membership

Estados oficiais:

1. `pending_approval`
2. `active`
3. `inactive`
4. `suspended_financial`
5. `revoked`
6. `expired`

### Politica de aprovacao

1. `Recepcionista` pode aprovar membership comum
2. `Manager` pode aprovar e revogar
3. `Owner` audita tudo e pode aprovar tudo

### Politica de primary_box e active_box

1. ao logar, o aluno cai no `primary_box`
2. ao trocar de box, o sistema muda o `active_box`
3. o sistema pode perguntar:
   - `Deseja tornar este seu box principal?`
4. `primary_box` nao deve ser sequestrado automaticamente por todo novo invite ou todo switch

### Politica de switch box

1. aparece na topbar quando houver `2+ memberships ativos`
2. lista apenas boxes ativos
3. ao escolher um box:
   - troca o `active_box`
   - recarrega o contexto
   - atualiza topbar
   - mostra feedback claro
4. nao exige novo login social por padrao
5. nao cria membership novo
6. nao procura box por email

### Politica de suspensao financeira

1. inadimplencia maior que `10 dias` leva o membership para `suspended_financial`
2. o aluno perde acesso ao app naquele box
3. identidade, historico e vinculo permanecem

### Politica de revogacao

1. se o membership for revogado:
   - o aluno nao opera mais naquele box
2. se o box revogado era o `active_box`:
   - promover outro membership ativo, se houver
   - ou cair em estado `sem box disponivel`
3. se o box revogado era o `primary_box`:
   - promover outro membership ativo
   - ou pedir nova definicao depois

### Estado obrigatorio de excecao

Se o aluno autenticar sem nenhum membership ativo, o app deve mostrar:

1. mensagem clara
2. CTA para `Entrar com convite`
3. CTA opcional para `Falar com seu box`

## A - Acao

## Fase 0 - Baseline consolidado

### O que fazer

1. aceitar o runtime atual como base
2. nao reescrever o que ja existe em `student_identity` e `student_app`
3. documentar que o fluxo atual ainda esta ancorado em `single-box`

### Ja existe

1. login social do aluno
2. invite landing
3. callback OAuth
4. cookie proprio do aluno
5. PWA do aluno
6. modelo `StudentIdentity`
7. modelo `StudentAppInvitation`
8. modelo `StudentTransfer`

### Pronto quando

1. a equipe parar de tratar a proxima fase como rewrite
2. o plano nascer em cima do runtime, nao contra ele

## Fase 1 - Hub de entrada

Status atual em 2026-04-17:

1. concluida

### O que fazer

1. transformar `/login/` em hub publico
2. criar `/login/funcionario/`
3. manter a tela atual do staff com `username + password`
4. destacar aluno como CTA principal

### O que entra

1. novo template do hub
2. view do hub
3. ajuste de rotas em `access`
4. microcopy com dica de favorito para a equipe

### O que nao entra

1. Google/Auth do staff
2. reescrita do backend do staff

### Pronto quando

1. `/login/` mostra `Aluno` x `Funcionario`
2. `/login/funcionario/` responde com o login atual
3. o fluxo do staff continua funcionando sem regressao

## Fase 2 - Contrato de membership

Status atual em 2026-04-17:

1. concluida

### O que fazer

1. introduzir o conceito de `membership` para o aluno
2. definir estados
3. separar `identity` de `membership`

### O que entra

1. modelagem de `StudentBoxMembership`
2. regras de aprovacao
3. estado `pending_approval`
4. trilha de auditoria minima

### O que nao entra

1. switch box ainda
2. multiplos boxes ativos simultaneos

### Pronto quando

1. o sistema para de depender de `single-box` como unico modelo futuro
2. o aluno pode ser representado como identidade + vinculos

## Fase 3 - Primary Box

Status atual em 2026-04-17:

1. concluida

### O que fazer

1. introduzir `primary_box` no contrato do aluno
2. garantir que o login sempre abre no box padrao

### Pronto quando

1. existe box padrao claramente definido
2. novo invite em outro box nao sequestra automaticamente o box principal

## Fase 4 - Active Box

Status atual em 2026-04-17:

1. concluida

### O que fazer

1. introduzir `active_box` como contexto de sessao
2. fazer o app ler o contexto ativo

### Pronto quando

1. toda tela relevante do aluno opera sobre `active_box`
2. o sistema consegue trocar contexto sem trocar identidade

## Fase 5 - Switch Box

Status atual em 2026-04-17:

1. concluida na base do runtime
2. ainda pode evoluir para promover `primary_box` com UX dedicada

### O que fazer

1. adicionar `Trocar box` na topbar
2. listar boxes ativos disponiveis
3. trocar `active_box` ao selecionar
4. opcionalmente perguntar se o novo box vira `primary_box`

### O que nao entra

1. re-login social por switch
2. criacao de membership novo por switch

### Pronto quando

1. o aluno troca contexto no app sem relogar
2. topbar reflete o box atual
3. feedback visual fica claro

## Fase 6 - Invite aberto e invite individual

Status atual em 2026-04-17:

1. concluida na primeira versao
2. invite individual ativa acesso ao fechar identidade
3. invite aberto do box cai em `pending_approval`
4. a operacao do box ja consegue aprovar membership pendente

### O que fazer

1. formalizar os dois tipos de invite
2. plugar aprovacao de membership
3. adicionar observabilidade

### Guardrails minimos

1. trilha de auditoria
2. medicao de uso
3. alerta por volume anormal

### Pronto quando

1. box pode distribuir invite sem transformar isso em acesso cego
2. a operacao enxerga convite aceito, pendente, expirado e abusivo

## Fase 7 - Governanca operacional

Status atual em 2026-04-17:

1. concluida na primeira versao
2. troca de e-mail ja respeita limite por papel
3. recepcao faz a 1a troca do mes; 2a troca exige Manager, Owner ou DEV
4. suspensao financeira, reativacao e revogacao ja operam sobre membership
5. a auditoria ja explica troca de e-mail, suspensao, reativacao e revogacao

### O que fazer

1. troca de email com limite por papel
2. aprovacao da 2a troca por `manager` ou `owner`
3. revogacao de membership
4. suspensao financeira
5. fallback quando perder `active_box` ou `primary_box`

### Pronto quando

1. a operacao nao depende de regra informal
2. auditoria consegue explicar o que aconteceu

## Fase 8 - Estados de excecao

Status atual em 2026-04-17:

1. concluida na primeira versao de UX
2. `aguardando aprovacao` ja existe
3. `sem box ativo` ja existe
4. `suspended_financial` ja possui tela propria
5. `entrar em outro box com convite` ja existe como ponte por token ou URL

### O que fazer

1. tela `sem box disponivel`
2. estado `aguardando aprovacao`
3. estado `suspended_financial`
4. fluxo `entrar em outro box com convite`

### Pronto quando

1. o app nao quebra semanticamente em cenarios incompletos
2. a UX continua clara mesmo fora do caminho feliz

## Fase 9 - Observabilidade, throttle e antifraude leve

Status atual em 2026-04-17:

1. concluida na primeira versao
2. `invite landing` ja possui throttle proprio por IP
3. `callback social` ja possui throttle proprio por IP
4. o cookie do aluno ja carrega `device_fingerprint` leve
5. o app do aluno ja derruba a sessao quando o fingerprint muda de forma forte
6. criacao de invite ja gera alerta de anomalia por ator e por box
7. aceite de invite/callback social ja gera alerta de anomalia por IP e por box

### O que fazer

1. manter throttle separado para cada corredor publico do aluno
2. observar rajadas suspeitas por:
   - ator
   - IP
   - box
3. deduplicar alertas para nao poluir auditoria
4. tratar fingerprint como sinal leve de risco, nao como prova absoluta

### Pronto quando

1. o sistema consegue desacelerar rajadas sem travar aluno legitimo com facilidade
2. a operacao consegue ver abuso antes de o banco encher de lixo
3. o runtime passa a ter cinto de seguranca sem virar bunker pesado demais

## Critérios de pronto globais

O plano esta funcionando quando:

1. o aluno entra por social login sem busca global de box
2. o funcionario continua entrando por `username + password`
3. invite contextualiza box
4. membership explicita vinculo
5. `primary_box` e `active_box` estao separados
6. switch box troca contexto sem relogar
7. troca de email e auditavel
8. inadimplencia suspende acesso sem apagar identidade
9. o sistema tolera aluno em mais de um box sem ambiguidade
10. o app mostra estado correto quando o aluno fica sem box ativo

## Failure checks

Se qualquer item abaixo acontecer, o plano foi implementado de forma errada:

1. login social decidir box por tentativa global
2. switch box criar membership novo
3. cambio de email sem trilha de auditoria
4. inadimplencia apagar identidade ou historico
5. novo invite em outro box roubar automaticamente o `primary_box`
6. login social do staff reaproveitar a logica do aluno
7. o hub `/login/` virar formulario hibrido confuso

## Resumo executivo

O mapa da obra e este:

1. manter a base pronta do aluno
2. criar um hub claro de entrada
3. elevar o modelo de `single-box` para `identity + membership`
4. separar `primary_box` de `active_box`
5. criar `switch box`
6. endurecer invite e governanca
7. fechar estados de excecao

Em linguagem de crianca:

1. o Google diz quem a pessoa e
2. o convite diz em qual casa ela pode entrar
3. o vinculo diz em quais casas ela tem chave
4. o box principal e a casa-base
5. o box ativo e a casa em que ela esta agora
