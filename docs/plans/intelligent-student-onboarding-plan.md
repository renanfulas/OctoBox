<!--
ARQUIVO: plano executavel do onboarding do aluno por tres jornadas oficiais.

TIPO DE DOCUMENTO:
- plano de execucao de produto + arquitetura + UX + operacao
- C.O.R.D.A. por ondas

AUTORIDADE:
- alta para a evolucao do onboarding do aluno

DOCUMENTOS PAIS:
- [../architecture/architecture-growth-plan.md](../architecture/architecture-growth-plan.md)
- [../architecture/center-layer.md](../architecture/center-layer.md)
- [student-access-invite-switch-corda.md](student-access-invite-switch-corda.md)

QUANDO USAR:
- quando a tarefa envolver convite do aluno, onboarding por link do box, lead importado via WhatsApp, convite para aluno ja cadastrado ou complemento de perfil
- quando precisarmos decidir a ordem certa de implementacao sem inflar o dominio do aluno nem criar wizard unico pesado
- quando quisermos orientar execucao por ondas pequenas, com baixo atrito para o box e baixo risco para o runtime

POR QUE ELE EXISTE:
- evita que a frente de onboarding do aluno vire uma ideia bonita, mas espalhada entre varios fluxos sem contrato claro
- transforma a estrategia em tres jornadas oficiais e uma tela de complemento posterior
- reduz atrito operacional do box sem reconstruir a base que ja existe em `student_identity` e `student_app`

O QUE ESTE ARQUIVO FAZ:
1. formaliza as tres jornadas oficiais de onboarding do aluno
2. define o que cada jornada sabe antes de o aluno entrar
3. organiza a implementacao em ondas curtas e executaveis
4. protege a arquitetura contra um wizard monolitico e contra onboarding pesado demais

PONTOS CRITICOS:
- onboarding nao deve ser confundido com matricula automatica por padrao
- o link em massa deve funcionar como portaria controlada, nao como porta dos fundos
- lead importado via WhatsApp deve usar o que o sistema ja sabe e pedir so o que falta
- aluno ja cadastrado nao deve passar por wizard desnecessario
- `editar perfil` existe para reduzir atrito inicial, nao para esconder ausencia de regra
-->

# Plano - Intelligent Student Onboarding

## 1. Resumo executivo

O OctoBox nao precisa de um onboarding novo do zero.

Ele precisa organizar melhor o que ja tem.

A estrategia oficial desta frente passa a ser:

1. `link em massa do box`
2. `convite individual para lead importado via WhatsApp`
3. `link para aluno ja cadastrado`
4. `editar perfil` como complemento posterior

Em linguagem simples:

1. uma rede para puxar a massa
2. um botao de precisao para recuperar caso a caso
3. uma entrada sem friccao para quem ja esta pronto
4. um perfil posterior para completar o que nao precisa bloquear a porta

## 2. C.O.R.D.A.

## C - Contexto

Hoje o runtime ja possui fundamentos importantes:

1. `StudentAppInvitation` para convite do app do aluno
2. `StudentIdentity` separado da conta de funcionario
3. callback OAuth com `Google` e `Apple`
4. `StudentBoxMembership` com estados formais
5. landing de invite por token
6. envio por e-mail
7. handoff para WhatsApp
8. tela operacional de convites em `student_identity`
9. fluxo atual para aluno ja cadastrado entrar no app

O problema atual nao e ausencia de mecanismo.

O problema atual e este:

1. os fluxos ainda parecem mais ferramenta operacional do que esteira clara de ativacao
2. ainda nao existe contrato oficial para tres jornadas diferentes
3. o box ainda precisa pensar demais sobre como convidar cada tipo de aluno
4. o sistema ainda nao usa de forma suficiente o que ja sabe sobre cada aluno

As tres jornadas oficiais agora sao:

1. `mass_box_invite`
2. `imported_lead_invite`
3. `registered_student_invite`

E a quarta peca de apoio e:

1. `post-entry-profile-edit`

## O - Objetivo

Implementar um onboarding do aluno mais facil para o box e mais leve para o aluno, com:

1. ativacao em massa por link do grupo do box
2. ativacao individual com 1 clique para lead importado via WhatsApp
3. ativacao direta para aluno ja cadastrado
4. complemento posterior de perfil sem travar a entrada
5. arquitetura leve, sem wizard unico monolitico

Sucesso significa:

1. o box consegue convidar a base com menos operacao manual
2. o aluno certo preenche so o necessario para o seu caso
3. o sistema reduz digitacao duplicada
4. a recepcao entra mais em excecao do que em rotina
5. a base continua coerente com `student_identity`, `membership` e `student_app`

## R - Riscos

### 1. Risco de wizard unico pesado

Se os tres fluxos forem empilhados em uma experiencia unica:

1. a manutencao fica confusa
2. a UX fica opaca
3. a arquitetura ganha acoplamento desnecessario

### 2. Risco de pedir dado demais cedo demais

Se a primeira entrada exigir mais informacao do que o caso pede:

1. cai conversao
2. aumenta abandono
3. onboarding vira formulario, nao corredor

### 3. Risco de abrir demais o link em massa

Se o link do grupo funcionar sem guardrail:

1. ex-aluno ou curioso pode entrar no fluxo errado
2. o box perde controle da fila
3. a operacao ganha ruido

### 4. Risco de onboarding virar matricula automatica

Se plano escolhido pelo aluno virar contrato automaticamente no primeiro corte:

1. o risco comercial sobe
2. a reversao fica cara
3. onboarding contamina o financeiro cedo demais

### 5. Risco de mover logica para a view

Se a diferenciacao entre jornadas ficar espalhada em template e view:

1. a regra fica dificil de testar
2. a evolucao fica cara
3. a arquitetura perde clareza

## D - Direcao

### Tese central

O onboarding do aluno deve seguir esta regra:

1. quanto menos o sistema sabe, mais onboarding
2. quanto mais o sistema sabe, menos atrito

Traducao pratica:

1. `mass_box_invite` usa wizard completo
2. `imported_lead_invite` usa wizard reduzido
3. `registered_student_invite` entra sem wizard
4. `editar perfil` absorve complemento posterior

### Frases de arquitetura

1. `Nao existe um onboarding; existem tres corredores oficiais de entrada.`
2. `Invite contextualiza; OAuth prova identidade; wizard fecha so o minimo util.`
3. `Editar perfil reduz friccao inicial e melhora dado ao longo do tempo.`
4. `Onboarding prepara acesso e qualificacao; nao substitui o fechamento financeiro por padrao.`
5. `A borda escolhe a jornada; o dominio continua dono da verdade transacional.`

### Regra de arquitetura leve

Esta frente deve respeitar:

1. `student_identity` continua dono de `invite`, `identity`, `delivery` e `membership`
2. `student_app` continua dono da experiencia posterior do aluno
3. a orquestracao das jornadas deve nascer como camada leve e testavel
4. a borda nao deve reinventar regra de negocio
5. o plano deve preferir evolucao sobre reescrita

### O que nao fazer

1. nao criar wizard gigante com dezenas de ramificacoes invisiveis
2. nao pedir CPF, saude ou cadastro pesado sem necessidade real desta frente
3. nao transformar escolha de plano em matricula automatica por padrao
4. nao duplicar cadastro do aluno quando o sistema ja conhece nome, telefone ou e-mail
5. nao espalhar logica de jornada em varios templates sem um contrato unico

## A - Acoes

### Onda 1 - Formalizar as tres jornadas oficiais

Objetivo:

1. fechar o contrato do produto antes de espalhar implementacao

Entregas:

1. registrar oficialmente:
   - `mass_box_invite`
   - `imported_lead_invite`
   - `registered_student_invite`
2. definir para cada jornada:
   - dados conhecidos
   - dados obrigatorios
   - tipo de wizard
   - estado final esperado
3. definir `editar perfil` como corredor posterior oficial

Criterio de pronto:

1. o time consegue explicar em uma frase quando cada jornada entra
2. a base deixa de tratar onboarding como um fluxo unico abstrato

### Onda 2 - Link em massa do box

Objetivo:

1. ativar a base com o menor custo operacional possivel

Escopo funcional:

1. 1 link ativo por box
2. validade de `30 dias`
3. limite de `200 cadastros`
4. OAuth obrigatorio
5. wizard completo
6. capacidade de:
   - copiar
   - regenerar
   - expirar antes
   - pausar

Campos do wizard completo:

1. nome
2. telefone
3. data de nascimento
4. e-mail
5. plano desejado ou plano selecionado
6. revisao final

Guardrails:

1. o link em massa deve funcionar como `portaria controlada`
2. a entrada por este fluxo nao deve pular a governanca do box
3. `plano` entra primeiro como dado de onboarding/comercial, nao como contrato automatico por padrao

Criterio de pronto:

1. o box consegue mandar 1 link no grupo e ver alunos entrando sem operacao manual unitária

### Onda 3 - Convite individual para lead importado via WhatsApp

Objetivo:

1. transformar lead importado em ativacao com 1 clique

Escopo funcional:

1. botao individual na aba de leads importados
2. handoff para WhatsApp com convite contextual
3. respeito a regras operacionais como:
   - limite de `25 convites` por janela operacional definida
4. status de rastreio por convite

Campos do wizard reduzido:

1. revisar nome
2. revisar telefone
3. data de nascimento
4. e-mail
5. plano

Regras:

1. nome e telefone ja conhecidos devem subir pre-preenchidos
2. o aluno corrige ou confirma, nao digita do zero
3. este fluxo deve ser mais curto que o link em massa

Criterio de pronto:

1. o box consegue recuperar caso a caso sem sair da operacao
2. lead importado deixa de exigir cadastro manual completo pela recepcao

### Onda 4 - Entrada direta para aluno ja cadastrado

Objetivo:

1. dar a melhor experiencia possivel para o caso mais maduro

Escopo funcional:

1. manter a entrada atual para aluno ja cadastrado
2. remover qualquer wizard desnecessario deste caminho
3. autenticar e entrar
4. complementar depois em `editar perfil`, se necessario

Regras:

1. se o sistema ja sabe o suficiente, nao pedir novamente
2. esse fluxo deve ser o mais curto de todos

Criterio de pronto:

1. aluno ja cadastrado entra no sistema praticamente sem atrito

### Onda 5 - Editar perfil posterior

Objetivo:

1. mover complemento de dados para depois da entrada sem perder qualidade de cadastro

Escopo funcional:

1. criar ou fortalecer a tela de `editar perfil`
2. permitir atualizar:
   - nome
   - e-mail
   - telefone
   - data de nascimento
3. preparar espaco para dados complementares futuros

Regras:

1. `editar perfil` serve para enriquecer, nao para travar a entrada inicial
2. a tela deve ser clara e segura para o aluno corrigir o proprio dado

Criterio de pronto:

1. o onboarding inicial fica leve
2. o sistema ainda consegue melhorar qualidade de dado depois

### Onda 6 - Observabilidade e fila de excecao

Objetivo:

1. deixar o box entender onde o onboarding esta funcionando e onde esta travando

Escopo funcional:

1. painel simples por jornada com:
   - enviados
   - autenticados
   - concluidos
   - pendentes
   - expirados
   - falhados
2. fila de excecoes para casos como:
   - e-mail divergente
   - lead nao reconciliado
   - convite expirado
   - tentativa sem correspondencia segura

Regras:

1. a fila de excecao deve chamar a operacao so quando necessario
2. o sistema deve continuar favorecendo o caminho simples

Criterio de pronto:

1. o box entende o que aconteceu com sua base sem precisar investigar tudo manualmente

## 3. Contrato das jornadas

## 3.1 Jornada 1 - `mass_box_invite`

### Quando usar

1. onboarding em massa no grupo do box
2. base ainda pouco estruturada

### O que o sistema sabe antes

1. contexto do box
2. limite e validade do link

### O que o aluno informa

1. nome
2. telefone
3. data de nascimento
4. e-mail
5. plano

### Tipo de experiencia

1. wizard completo

### Saida esperada

1. identidade criada ou consolidada
2. entrada controlada no fluxo do box

## 3.2 Jornada 2 - `imported_lead_invite`

### Quando usar

1. lead importado via WhatsApp
2. ativacao individual assistida

### O que o sistema sabe antes

1. nome
2. telefone

### O que o aluno informa

1. confirma ou corrige nome
2. confirma ou corrige telefone
3. data de nascimento
4. e-mail
5. plano

### Tipo de experiencia

1. wizard reduzido

### Saida esperada

1. lead reconciliado com identidade valida
2. menor carga manual para a recepcao

## 3.3 Jornada 3 - `registered_student_invite`

### Quando usar

1. aluno ja cadastrado no sistema

### O que o sistema sabe antes

1. nome
2. e-mail e/ou outros dados essenciais ja existentes

### O que o aluno informa

1. nada no onboarding inicial, salvo autenticacao

### Tipo de experiencia

1. sem wizard

### Saida esperada

1. acesso ativado com minimo de cliques

## 3.4 Jornada 4 - `post-entry-profile-edit`

### Quando usar

1. depois da entrada
2. quando o aluno quiser ou precisar complementar dados

### Tipo de experiencia

1. perfil editavel posterior

### Saida esperada

1. mais qualidade de dado sem prejudicar ativacao inicial

## 4. Ordem recomendada de execucao

1. Onda 1 - formalizar as jornadas
2. Onda 2 - link em massa do box
3. Onda 3 - convite individual para lead importado
4. Onda 4 - entrada direta para aluno ja cadastrado
5. Onda 5 - editar perfil posterior
6. Onda 6 - observabilidade e fila de excecao

## 5. Encaixe tecnico por onda

## 5.1 Regra de ownership

Antes de detalhar as ondas, a divisao tecnica desta frente deve obedecer esta regra:

### `student_identity`

Fica dono de:

1. `invite`
2. `identity`
3. `membership`
4. entrega de convite
5. governanca de aceite e pendencia

Arquivos-base atuais:

1. `student_identity/models.py`
2. `student_identity/views.py`
3. `student_identity/staff_views.py`
4. `student_identity/application/use_cases.py`
5. `student_identity/infrastructure/repositories.py`
6. `student_identity/notifications.py`
7. `templates/student_identity/*`

### `student_app`

Fica dono de:

1. wizard do aluno depois da autenticacao
2. experiencia do aluno dentro do app
3. `editar perfil`
4. estados visiveis do aluno apos entrada

Arquivos-base atuais:

1. `student_app/views.py`
2. `student_app/urls.py`
3. `student_app/forms.py`
4. `student_app/application/use_cases.py`
5. `templates/student_app/*`

### `onboarding`

Fica dono de:

1. intake
2. leads importados
3. fila operacional ligada ao box
4. disparo contextual do fluxo individual para lead importado

Arquivos-base atuais:

1. `onboarding/views.py`
2. `onboarding/queries.py`
3. `onboarding/presentation.py`
4. `templates/onboarding/*`

### `communications`

Fica dono de:

1. toque operacional de mensagem
2. handoff e corredor de envio
3. integracao com WhatsApp como infraestrutura de entrega

Arquivos-base atuais:

1. `communications/facade/messaging.py`
2. `communications/application/*`
3. `communications/infrastructure/*`

### `students` e `catalog`

Ficam donos de:

1. dado canonico do aluno
2. complemento posterior de campos como:
   - `birth_date`
   - `email`
   - `gender`
3. formularios operacionais existentes do cadastro tradicional

Arquivos-base atuais:

1. `students/model_definitions.py`
2. `catalog/form_definitions/student_forms.py`

## 5.2 Onda 1 - Formalizar as tres jornadas oficiais

### Onde encaixa tecnicamente

#### Documento e contrato

1. este plano e a fonte principal da frente
2. `student_identity` passa a carregar o contrato logico das jornadas

#### Camada recomendada

1. criar uma camada leve de orquestracao em `student_identity`
2. essa camada pode nascer como:
   - `student_identity/presentation.py` expandido
   - ou `student_identity/facade/` se a frente crescer o suficiente

### O que entra nesta onda

1. definicao formal de:
   - `mass_box_invite`
   - `imported_lead_invite`
   - `registered_student_invite`
2. definicao dos estados de entrada e saida
3. definicao de qual jornada chama qual tela

### O que nao entra ainda

1. wizard novo completo
2. modelagem pesada nova
3. integracao nova de envio em massa

### Ownership principal

1. `student_identity`
2. com alinhamento de `student_app` e `onboarding`

## 5.3 Onda 2 - Link em massa do box

### Onde encaixa tecnicamente

#### Dominio e verdade transacional

1. `student_identity/models.py`
2. `student_identity/application/use_cases.py`
3. `student_identity/infrastructure/repositories.py`

#### Borda operacional e governanca

1. `student_identity/staff_views.py`
2. `student_identity/presentation.py`
3. `templates/student_identity/operations_invites.html`

#### Entrada publica do aluno

1. `student_identity/views.py`
2. `student_identity/urls.py`
3. `templates/student_identity/invite_landing.html`

#### Wizard do aluno

1. `student_app/views.py`
2. `student_app/urls.py`
3. `student_app/forms.py`
4. `templates/student_app/*`

### Conteudo tecnico que entra aqui

1. criar a nocao de `link em massa do box` como evolucao do `open_box`
2. suportar:
   - limite de usos
   - validade de 30 dias
   - pausa
   - revogacao
3. direcionar o aluno autenticado para o wizard completo no `student_app`

### Guardrail de encaixe

1. `student_identity` decide permissao, validade, token e membership
2. `student_app` decide UX do wizard
3. `students` continua dono do dado do aluno depois da confirmacao

## 5.4 Onda 3 - Convite individual para lead importado via WhatsApp

### Onde encaixa tecnicamente

#### Origem operacional

1. `onboarding/views.py`
2. `onboarding/queries.py`
3. `templates/onboarding/*`

#### Convite e governanca

1. `student_identity/staff_views.py`
2. `student_identity/application/use_cases.py`
3. `student_identity/infrastructure/repositories.py`

#### Handoff de mensagem

1. `student_identity/notifications.py`
2. `communications/facade/messaging.py` quando a frente precisar sair do simples handoff e ganhar corredor mais oficial

#### Wizard reduzido

1. `student_app/views.py`
2. `student_app/forms.py`
3. `templates/student_app/*`

### Conteudo tecnico que entra aqui

1. botao de 1 clique a partir do lead importado
2. reaproveitamento de `nome` e `telefone` como dados pre-preenchidos
3. handoff via WhatsApp
4. limite operacional de convites por janela
5. wizard reduzido contextual

### Guardrail de encaixe

1. `onboarding` descobre e aciona
2. `student_identity` gera e governa
3. `communications` entrega ou apoia a entrega
4. `student_app` coleta complemento do aluno

### Risco tecnico a evitar

1. nao colocar logica de convite dentro do `onboarding/views.py`
2. o `onboarding` deve chamar o corredor, nao virar dono do fluxo de identidade

## 5.5 Onda 4 - Entrada direta para aluno ja cadastrado

### Onde encaixa tecnicamente

1. `student_identity/views.py`
2. `student_identity/application/use_cases.py`
3. `student_identity/infrastructure/repositories.py`
4. `student_app/views.py`

### Conteudo tecnico que entra aqui

1. limpar a jornada existente
2. garantir que aluno ja conhecido nao caia em wizard desnecessario
3. reforcar o roteamento:
   - autenticou
   - entrou
   - usa

### Guardrail de encaixe

1. nao duplicar regra do wizard aqui
2. nao mover esse caso para o fluxo de massa

### Ownership principal

1. `student_identity`
2. com suporte de `student_app`

## 5.6 Onda 5 - Editar perfil posterior

### Onde encaixa tecnicamente

#### UX e fluxo

1. `student_app/views.py`
2. `student_app/urls.py`
3. `templates/student_app/settings.html`
4. novos templates/partials em `templates/student_app/*` se necessario

#### Formulario

1. `student_app/forms.py`
2. ou formulario reaproveitado/adaptado a partir de campos de `catalog/form_definitions/student_forms.py`

#### Persistencia do dado

1. `students/model_definitions.py`
2. `student_identity/infrastructure/repositories.py` se houver ajuste de e-mail/identity em conjunto

### Conteudo tecnico que entra aqui

1. tela de editar perfil
2. atualizacao segura de:
   - nome
   - e-mail
   - telefone
   - data de nascimento
3. possivel sincronizacao entre `Student` e `StudentIdentity` quando o e-mail mudar

### Guardrail de encaixe

1. o perfil nao deve reinventar o cadastro operacional inteiro do `catalog`
2. a tela do aluno deve expor so o que faz sentido para autoedicao

## 5.7 Onda 6 - Observabilidade e fila de excecao

### Onde encaixa tecnicamente

#### Painel operacional

1. `student_identity/staff_views.py`
2. `student_identity/presentation.py`
3. `templates/student_identity/operations_invites.html`

#### Dados e agregacoes

1. extrair leitura pesada de `student_identity/staff_views.py` para:
   - `student_identity/queries.py` se a complexidade crescer
   - ou uma camada de snapshot/presentation mais clara

#### Operacao de leads e intake

1. `onboarding/queries.py`
2. `onboarding/views.py`

### Conteudo tecnico que entra aqui

1. status por jornada
2. fila de excecao
3. visao de:
   - enviados
   - autenticados
   - concluidos
   - pendentes
   - expirados
   - falhados
4. conciliacao entre lead, convite e identidade

### Guardrail de encaixe

1. `AuditEvent` pode apoiar rastreabilidade
2. `AuditEvent` nao deve virar read model final desta frente
3. a leitura consolidada deve ser tratada como snapshot operacional

## 5.8 Sequencia tecnica recomendada

Para evitar peso e retrabalho, a sequencia tecnica sugerida e:

1. consolidar contrato logico das jornadas em `student_identity`
2. criar o link em massa e o wizard completo
3. plugar o botao individual da aba de leads no corredor oficial
4. limpar a entrada direta do aluno ja cadastrado
5. abrir `editar perfil`
6. so depois refinar observabilidade e fila de excecao

## 6. Regra curta

O melhor onboarding nao e o que pede tudo.

O melhor onboarding e o que pede so o necessario para cada aluno entrar pelo corredor certo.
