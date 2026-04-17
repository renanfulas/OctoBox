<!--
ARQUIVO: C.O.R.D.A. da area do aluno com home dinamica, grade, WOD e RM.

TIPO DE DOCUMENTO:
- plano arquitetural e de experiencia
- trilho de execucao por ondas

AUTORIDADE:
- alta para a proxima fase do app do aluno

DOCUMENTOS PAIS:
- [../architecture/octobox-mobile-architecture.md](../architecture/octobox-mobile-architecture.md)
- [octobox-mobile-execution-plan.md](octobox-mobile-execution-plan.md)
- [../experience/octobox-mobile-guide.md](../experience/octobox-mobile-guide.md)
- [student-access-invite-switch-corda.md](student-access-invite-switch-corda.md)

QUANDO USAR:
- quando a duvida for como evoluir o app do aluno depois da fundacao de acesso
- quando precisarmos decidir a home do aluno, o papel da grade, do WOD e do RM
- quando quisermos implementar por ondas sem misturar UX, dados de treino e logica de box

POR QUE ELE EXISTE:
- evita que Grade, WOD e RM nascam como telas soltas sem um fluxo de produto coerente
- transforma a intuicao de habito e uso recorrente em regras executaveis
- protege a arquitetura contra acoplamento entre prescricao do coach e dados pessoais do aluno

O QUE ESTE ARQUIVO FAZ:
1. formaliza a home dinamica do aluno
2. define o papel de Grade, WOD e RM dentro do app
3. separa contratos de UX, dominio e dados
4. organiza a implementacao em ondas pequenas com checks objetivos

PONTOS CRITICOS:
- o app do aluno nao pode virar copia comprimida do web
- a home nao deve ser fixa se o momento do aluno mudou
- WOD nao deve guardar RM do aluno
- RM nao deve nascer como texto solto ou campo improvisado
- Grade e WOD precisam continuar existindo como destinos explicitos, mesmo com home dinamica
-->

# C.O.R.D.A. - App do aluno com Grade, WOD e RM

## C - Contexto

O app do aluno ja saiu da fase de acesso basico e hoje possui uma fundacao importante:

1. identidade propria do aluno
2. invite contextual por box
3. membership por box
4. `primary_box`
5. `active_box`
6. `switch box`
7. estados de excecao do app
8. PWA online-first

Isso significa que a porta do predio ja existe.

Agora a pergunta nao e mais "como ele entra?".

A pergunta passa a ser:

1. o que ele ve primeiro?
2. o que faz ele abrir o app varias vezes ao dia?
3. como o app deixa de ser calendario passivo e vira ferramenta de treino?

### Tese de produto

O aluno vive dois momentos mentais diferentes:

1. antes da aula: quer saber `qual aula eu tenho?`
2. durante a aula: quer saber `qual treino eu faco agora e com qual carga?`

Logo, a experiencia central do app nao deve ser estatica.

Ela deve mudar conforme o momento operacional do aluno.

### Tese de experiencia

`Grade` e o modo de chegada.

`WOD` e o modo de execucao.

`RM` e a camada de personalizacao que transforma um treino generico em treino pessoal.

Em linguagem simples:

1. a Grade mostra a porta da sala
2. o WOD mostra a licao da aula
3. o RM mostra o tamanho certo do caderno daquela crianca

## O - Objetivo

Construir a proxima fase do app do aluno para que:

1. `Inicio` seja uma home dinamica orientada ao contexto do aluno
2. `Grade` seja a tela principal antes do treino
3. `WOD` vire a tela principal quando o treino estiver ativo
4. `RM` nasca como fundacao de personalizacao, mesmo que a inteligencia completa venha depois
5. a navegacao fique limpa no mobile e no desktop
6. o fluxo seja implementado por ondas pequenas, sem reescrever a base pronta

### Sucesso significa

1. o aluno abre e entende em menos de 1 segundo onde esta
2. o app mostra o que importa no momento atual
3. o aluno comeca a abrir o app repetidamente durante o dia de treino
4. o sistema nao espalha regra de contexto por varias views sem dono
5. o WOD pode consultar o RM do aluno sem acoplamento ruim

## R - Riscos

### 1. Risco de home dinamica virar gambiarra

Se cada view decidir sozinha se mostra Grade ou WOD:

1. o comportamento fica inconsistente
2. o debug fica ruim
3. nasce debito tecnico rapido

### 2. Risco de RM virar campo solto no perfil

Se RM nascer como texto ou observacao:

1. nao serve direito para calculo
2. nao serve direito para historico
3. nao escala para recomendacao automatica

### 3. Risco de WOD guardar dados pessoais do aluno

Se o WOD salvar a carga do aluno dentro da prescricao:

1. o coach passa a misturar regra coletiva com dado individual
2. evolucao futura fica cara
3. qualquer mudanca de RM exige regravacao torta

### 4. Risco de mobile ficar pesado por excesso de navegacao

Se colocarmos sidebar completa e densa no celular:

1. a experiencia perde velocidade mental
2. a interface parece web comprimido

### 5. Risco de querer inteligencia cedo demais

Se tentarmos fazer estimativa, progresso, historico avancado e personalizacao profunda logo no inicio:

1. o tempo de entrega explode
2. a base conceitual nasce apressada
3. aumenta o risco de refacao

## D - Direcao

### Tese central

O app do aluno deve operar com uma home resolvida por contexto, mas com destinos explicitos e previsiveis.

### Frases de arquitetura

1. `Inicio` escolhe o contexto; `Grade` e `WOD` continuam existindo como paginas reais.
2. `WOD` guarda a regra de prescricao; `RM` guarda a capacidade do aluno.
3. O app personaliza a carga; o coach nao precisa prescrever carga por aluno.
4. O mobile deve parecer favorito de bolso, nao dashboard encolhido.

### Modo oficial da home

#### `schedule_default`
Usar quando:

1. o aluno nao confirmou presenca hoje
2. nao existe aula ativa
3. nao existe treino do dia publicado para a janela atual

Home mostra:

1. `Grade de aulas`
2. proxima aula
3. CTA para confirmar presenca

#### `wod_active`
Usar quando:

1. o aluno confirmou presenca
2. existe janela de treino ativa
3. existe WOD publicado

Home mostra:

1. `WOD`
2. blocos do treino
3. carga recomendada quando houver `% RM`
4. CTA secundario para voltar a `Grade`

#### `membership_pending`
Ja existe e continua valendo.

#### `financial_suspended`
Ja existe e continua valendo.

#### `no_active_box`
Ja existe e continua valendo.

### Regra de transicao Grade -> WOD

O app troca a home principal quando:

1. o aluno confirmou presenca
2. existe aula/slot do dia
3. existe WOD publicado para o contexto
4. estamos dentro da janela de treino

### Regra de retorno WOD -> Grade

1. a janela de treino expirou
2. a aula terminou
3. o treino nao esta mais ativo
4. o aluno navega manualmente para Grade

## A - Arquitetura-alvo

## 1. Navegacao e shell

### Estrutura base

#### Desktop
1. topbar
2. sidebar
3. area central com `Inicio`, `Grade`, `WOD`, `RM`, `Perfil`

#### Mobile
1. topbar compacta
2. navegacao leve por tabbar inferior ou menu sheet
3. nada de sidebar pesada como experiencia primaria

### Elementos da topbar

1. avatar do aluno
2. nome do `active_box`
3. toggle de tema
4. acao `Trocar box`

## 2. Mapa de paginas

### `Inicio`
- pagina resolvida por contexto

### `Grade`
- agenda e proxima aula
- status da reserva
- confirmacao de presenca

### `WOD`
- treino do dia
- blocos de treino
- recomendacao por aluno quando existir

### `RM`
- records do aluno por movimento
- atualizacao simples de RM

### `Perfil`
- identidade, box, configuracoes, saida

## 3. Dominio e contratos

### 3.1 `Movement`
Catalogo de movimentos.

Exemplos:

1. deadlift
2. back squat
3. snatch
4. clean

Regra:
- movimento precisa ter ID canonico
- o sistema nao deve depender de texto livre

### 3.2 `StudentRM`
Capacidade do aluno por movimento.

Campos conceituais:

1. `student_identity`
2. `movement`
3. `rm_value`
4. `unit`
5. `recorded_at`
6. `source`

### 3.3 `WorkoutPrescription`
Prescricao do coach para o WOD.

Campos conceituais:

1. `movement`
2. `sets`
3. `reps`
4. `load_type`
5. `load_value`

### 3.4 `WorkoutRecommendationService`
Servico de dominio que:

1. le a prescricao
2. consulta o RM do aluno
3. calcula a carga recomendada
4. devolve uma leitura pronta para a UI

### Regra de ouro

`WOD` nao guarda o RM do aluno.

`RM` nao guarda a prescricao do WOD.

O motor do app une os dois no momento da leitura.

## 4. UX esperada

### Home em modo Grade

Deve responder:

1. qual e minha proxima aula?
2. ja confirmei presenca?
3. quando o treino entra?

### Home em modo WOD

Deve responder:

1. qual e o treino de agora?
2. qual exercicio vem?
3. que carga eu devo usar?

### RM

Deve responder:

1. qual e meu RM atual?
2. quando ele foi atualizado?
3. como ajustar isso rapido?

## 5. Estrategia de implementacao por ondas

### Onda 0 - Contrato e fundacao visual

#### Objetivo
Fechar o contrato de shell e navegacao da area do aluno.

#### Entregas
1. sitemap da area do aluno
2. contrato de `Inicio`, `Grade`, `WOD`, `RM`, `Perfil`
3. desenho de topbar
4. decisao final de navegacao mobile

#### Checks
1. `Inicio` foi definido como contexto, nao como pagina fixa?
2. `Grade` e `WOD` continuam acessiveis explicitamente?
3. a navegacao mobile ficou mais leve que a web?

#### Failure checks
1. se a home depende de varios redirects espalhados, a onda falhou
2. se o mobile parece dashboard desktop comprimido, a onda falhou

### Onda 1 - Shell do app do aluno

#### Objetivo
Construir a estrutura visual base da nova area do aluno.

#### Entregas
1. topbar oficial do aluno
2. sidebar no desktop
3. navegacao mobile leve
4. placeholders de `Inicio`, `Grade`, `WOD`, `RM`, `Perfil`

#### Arquivos provaveis
1. `templates/student_app/layout.html`
2. `templates/student_app/home.html`
3. `templates/student_app/grade.html`
4. `templates/student_app/wod.html`
5. `templates/student_app/rm.html`
6. `static/css/student_app/app.css`

#### Checks
1. a shell abre limpa e respiravel?
2. a navegacao bate com o guia mobile do OctoBox?
3. o mobile-first foi respeitado?

### Onda 2 - Home dinamica

#### Objetivo
Fazer `Inicio` escolher entre `Grade` e `WOD`.

#### Entregas
1. `StudentHomeResolver` ou servico equivalente
2. estados formais da home
3. regra de janela de treino
4. fallback seguro para `Grade`

#### Checks
1. existe um unico lugar dono da decisao?
2. o estado da home e explicavel?
3. o comportamento e previsivel para o aluno?

#### Failure checks
1. se cada view decide a home por conta propria, a onda falhou
2. se `Inicio` some e confunde o usuario, a onda falhou

### Onda 3 - Grade como modo de chegada

#### Objetivo
Transformar `Grade` em tela de rotina e preparacao.

#### Entregas
1. proxima aula em destaque
2. CTA de confirmar presenca
3. lista compacta da semana
4. indicacao clara de que o WOD aparece quando o treino estiver ativo

#### Checks
1. o aluno entende rapidamente o proximo passo?
2. a grade parece viva e nao tabela burocratica?
3. o CTA principal esta claro?

### Onda 4 - WOD como modo de execucao

#### Objetivo
Criar a leitura rapida do treino do dia.

#### Entregas
1. pagina de WOD do dia
2. blocos de treino legiveis
3. leitura em menos de 1 segundo mental
4. estrutura preparada para recomendacao de carga

#### Checks
1. o aluno consegue abrir no meio da aula e achar o que precisa?
2. o WOD esta orientado a execucao, nao a leitura longa?
3. o retorno para `Grade` esta facil?

### Onda 5 - Fundacao de RM

#### Objetivo
Criar a base correta de dados para records maximos.

#### Entregas
1. catalogo de movimentos
2. modelo `StudentRM`
3. pagina `RM`
4. atualizacao simples de RM

#### Checks
1. RM esta estruturado por movimento canonico?
2. existe data e origem do RM?
3. nao ha texto solto como fonte oficial?

#### Failure checks
1. se o nome do movimento e texto livre, a onda falhou
2. se o RM nasceu so como campo de perfil, a onda falhou

### Onda 6 - Ligacao WOD -> RM

#### Objetivo
Personalizar o WOD com base no RM do aluno.

#### Entregas
1. `WorkoutRecommendationService`
2. suporte a `load_type = percentage_of_rm`
3. exibicao de carga recomendada
4. mensagem explicativa simples na UI

#### Exemplo
1. RM deadlift = `100 kg`
2. WOD = `5x10 @ 70%`
3. recomendacao = `70 kg`

#### Checks
1. a recomendacao e calculada fora do template?
2. o WOD continua sendo regra coletiva?
3. o aluno entende de onde veio a carga?

### Onda 7 - Polimento e habito

#### Objetivo
Refinar a experiencia para retorno diario.

#### Entregas
1. microcopy clara
2. feedback de presenca confirmada
3. indicacao de treino ativo
4. refinamento de densidade visual
5. melhoria de abertura rapida no mobile

#### Checks
1. o app ficou gostoso de abrir varias vezes?
2. o fluxo Grade -> WOD parece natural?
3. a area do aluno tem cara de produto favorito, nao de painel inchado?

## 6. Ordem oficial de rollout

### Ordem obrigatoria
1. Onda 0 - contrato e fundacao visual
2. Onda 1 - shell
3. Onda 2 - home dinamica
4. Onda 3 - Grade
5. Onda 4 - WOD
6. Onda 5 - fundacao de RM
7. Onda 6 - ligacao WOD -> RM
8. Onda 7 - polimento

### Motivo
1. sem shell, o resto nasce solto
2. sem home dinamica, Grade e WOD perdem a tese central
3. sem WOD, o RM vira numero sem uso
4. sem fundacao de RM, a ligacao com WOD vira gambiarra

## 7. Regras de CSS e front-end

### Regras obrigatorias
1. CSS modular por pagina e componente
2. nada de logica de calculo no template
3. nada de inline style
4. mobile-first
5. foco em leitura imediata

### Direcao visual
1. clean
2. branco
3. respiravel
4. premium
5. profundo sem parecer pesado

### Regra de densidade
Se a pessoa precisa parar e pensar onde clicar, a tela esta pesada demais.

## 8. Fora de escopo agora

1. training max
2. estimativa automatica de novo RM
3. historico profundo de performance
4. analytics avancado de treino
5. IA de recomendacao de carga
6. predicao de fadiga

Essas pecas podem entrar depois.

Elas nao sao prerequisito para provar o produto.

## 9. Criterios de pronto gerais

O plano esta bem executado quando:

1. o aluno abre e sabe onde esta instantaneamente
2. `Grade` resolve o antes do treino
3. `WOD` resolve o durante o treino
4. `RM` deixa de ser decoracao e vira fundacao de personalizacao
5. o app parece favorito de bolso
6. a arquitetura continua simples de evoluir

## 10. Resumo executivo

O plano do app do aluno fica assim:

1. `Inicio` resolve contexto
2. `Grade` organiza a chegada
3. `WOD` conduz a execucao
4. `RM` personaliza a carga
5. tudo cresce em ondas pequenas com checks claros

Em linguagem de crianca:

1. primeiro a crianca olha qual sala vai
2. depois ela senta e ve a licao
3. o caderno dela tem o tamanho certo para a mao dela

Se fizermos nessa ordem, o app nao vira um monte de telas bonitas sem alma.

Ele vira ferramenta de rotina, depois ferramenta de treino, e depois favorito.
