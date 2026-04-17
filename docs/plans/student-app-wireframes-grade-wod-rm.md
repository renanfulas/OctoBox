<!--
ARQUIVO: wireframes tecnicos da area do aluno para Inicio, Grade, WOD e RM.

TIPO DE DOCUMENTO:
- blueprint de interface
- apoio direto a implementacao front-end

AUTORIDADE:
- media-alta para a fase visual e estrutural da area do aluno

DOCUMENTOS PAIS:
- [student-app-grade-wod-rm-corda.md](student-app-grade-wod-rm-corda.md)
- [octobox-mobile-screen-blueprint.md](octobox-mobile-screen-blueprint.md)
- [../experience/octobox-mobile-guide.md](../experience/octobox-mobile-guide.md)

QUANDO USAR:
- antes de codar a shell do aluno
- quando a duvida for "o que entra em cada tela?"
- quando precisarmos decidir hierarquia visual, CTA principal e estados de cada superficie

POR QUE ELE EXISTE:
- evita improviso na implementacao do app do aluno
- transforma tese de produto em blocos concretos de interface
- garante que Grade, WOD e RM nascam com hierarquia certa

O QUE ESTE ARQUIVO FAZ:
1. define wireframes tecnicos de Inicio, Grade, WOD e RM
2. define blocos obrigatorios, opcionais e estados
3. indica prioridades visuais e comportamento mobile-first
4. orienta implementacao sem acoplar front-end e dominio do jeito errado

PONTOS CRITICOS:
- Inicio e tela de contexto, nao pagina fixa
- Grade precisa parecer rotina simples, nao tabela burocratica
- WOD precisa parecer ferramenta de treino, nao texto longo
- RM precisa nascer simples, mas estruturado
-->

# Wireframes tecnicos - area do aluno

## Tese geral

O app do aluno deve obedecer esta ordem mental:

1. `Inicio` mostra o que importa agora
2. `Grade` organiza a rotina
3. `WOD` guia a execucao do treino
4. `RM` personaliza a experiencia

Em linguagem simples:

1. Inicio pergunta "onde voce esta agora?"
2. Grade responde "qual e sua proxima aula?"
3. WOD responde "o que voce faz agora?"
4. RM responde "qual e o seu peso certo?"

## Regras globais de interface

### Regra 1
No mobile, a leitura principal deve caber em um olhar curto.

### Regra 2
Cada tela deve ter um CTA principal claro.

### Regra 3
Nada de tabela densa como primeiro contato.

### Regra 4
Topbar sempre visivel com:

1. avatar
2. box atual
3. tema
4. acesso a menu

### Regra 5
No mobile, usar:

1. tabbar inferior ou menu sheet leve
2. nada de sidebar pesada como navegacao primaria

## Shell base

### Topbar

#### Conteudo
1. avatar do aluno
2. nome resumido do box atual
3. toggle de tema
4. botao menu/perfil

#### Comportamento
1. box atual pode abrir `Trocar box`
2. avatar abre `Perfil`

### Navegacao principal

#### Mobile
1. `Inicio`
2. `Grade`
3. `WOD`
4. `RM`
5. `Perfil` via menu ou avatar

#### Desktop
1. sidebar com os mesmos destinos
2. destaque claro do item ativo

---

# 1. Wireframe - Inicio

## Papel da tela

`Inicio` e uma tela resolvida por contexto.

Ela nao e fixa.

Ela pode estar em:

1. modo `Grade`
2. modo `WOD`
3. estados especiais herdados do acesso

## 1A. Inicio em modo Grade

### Objetivo
Mostrar o proximo compromisso e conduzir a confirmacao de presenca.

### Hierarquia

#### Bloco 1 - Header contextual
Conteudo:
1. saudacao curta
2. data de hoje
3. box atual

Exemplo:
- `Boa noite, Renan`
- `Hoje, quarta-feira`
- `MFIT Personal`

#### Bloco 2 - Card principal da proxima aula
Conteudo:
1. nome da aula
2. horario
3. coach
4. status da reserva
5. CTA principal

CTA principal:
1. `Confirmar presenca`
2. ou `Ver aula`

#### Bloco 3 - Janela de treino
Conteudo:
1. texto curto explicando que o WOD aparece quando a presenca estiver confirmada

Exemplo:
- `Quando sua presenca for confirmada, o treino de hoje aparece aqui em destaque.`

#### Bloco 4 - Proximas aulas
Conteudo:
1. lista curta da semana
2. no maximo 3 a 5 cards

#### Bloco 5 - Atalhos leves
Conteudo:
1. `Abrir Grade`
2. `Ver RM`

### Wireframe textual

```text
[Topbar]

Boa noite, Renan
Hoje, quarta-feira

[Card principal]
Cross Training
19:00 - Coach Ana
Reserva confirmada / aguardando
[Confirmar presenca]

[Card informativo]
Seu treino do dia aparece aqui quando sua presenca estiver confirmada.

[Lista curta]
Proximas aulas da semana
- Quinta 07:00
- Sexta 19:00
- Sabado 09:00

[Atalhos]
Ver grade completa | Ver RM
```

### CTA principal
`Confirmar presenca`

### CTA secundario
`Ver grade completa`

### Estado vazio
Se nao houver aula agendada:
1. mostrar mensagem calma
2. CTA para explorar Grade

Exemplo:
- `Nenhuma aula agendada para hoje.`
- `[Abrir grade]`

## 1B. Inicio em modo WOD

### Objetivo
Virar painel rapido de consulta durante o treino.

### Hierarquia

#### Bloco 1 - Header contextual
Conteudo:
1. `Treino de hoje ativo`
2. horario da aula
3. coach

#### Bloco 2 - Card principal do WOD
Conteudo:
1. titulo do treino
2. bloco atual ou primeiro bloco
3. CTA principal

CTA principal:
1. `Abrir WOD completo`

#### Bloco 3 - Resumo rapido de carga
Se existir `% RM`:
1. movimento
2. regra
3. carga recomendada

Exemplo:
- `Deadlift`
- `5 x 10 @ 70% do seu RM`
- `Carga recomendada: 70 kg`

#### Bloco 4 - Continuidade
Conteudo:
1. CTA para `Ver Grade`
2. CTA para `Ver RM`

### Wireframe textual

```text
[Topbar]

Treino de hoje ativo
Aula confirmada - 19:00

[Card principal]
WOD do dia
Forca + Metcon
[Abrir WOD completo]

[Card de recomendacao]
Deadlift
5 x 10 @ 70% do seu RM
Carga recomendada: 70 kg

[Atalhos]
Ver grade | Ver RM
```

### CTA principal
`Abrir WOD completo`

### CTA secundario
`Ver grade`

### Failure check
Se o aluno abrir essa home e ainda precisar procurar o treino, a tela falhou.

---

# 2. Wireframe - Grade

## Papel da tela

A `Grade` e a agenda operacional do aluno.

Ela nao deve parecer tabela do backoffice.

Ela deve parecer:

1. simples
2. clara
3. facil de tocar

## Estrutura

### Bloco 1 - Header
Conteudo:
1. titulo `Grade`
2. subtitulo curto

Exemplo:
- `Sua rotina no box`

### Bloco 2 - Filtro leve
Conteudo:
1. `Hoje`
2. `Semana`
3. opcionalmente `Proximas`

### Bloco 3 - Card da proxima aula
Conteudo:
1. destaque visual da aula mais proxima
2. CTA de confirmar presenca

### Bloco 4 - Lista de aulas
Cada item mostra:
1. dia
2. horario
3. modalidade
4. coach
5. status

### Bloco 5 - Estado de treino ativo
Se o aluno ja confirmou presenca e a janela estiver ativa:
1. mostrar banner curto
2. CTA `Ir para WOD`

### Wireframe textual

```text
[Topbar]

Grade
Sua rotina no box

[Filtro]
Hoje | Semana

[Card destaque]
Proxima aula
Cross Training
19:00 - Coach Ana
[Confirmar presenca]

[Lista]
Hoje - 19:00 - Cross Training - Confirmada
Amanha - 07:00 - Mobility - Disponivel
Sexta - 19:00 - Strength - Disponivel

[Banner opcional]
Seu treino de hoje ja esta ativo
[Ir para WOD]
```

### CTA principal
`Confirmar presenca`

### CTA secundario
`Ir para WOD` quando fizer sentido

### Estado vazio
1. texto calmo
2. CTA para atualizar ou verificar outra semana

### Failure check
Se a Grade exigir leitura longa para achar a proxima aula, a tela falhou.

---

# 3. Wireframe - WOD

## Papel da tela

O `WOD` e a ferramenta de execucao.

Ela deve ser rapida de consultar no meio do treino.

Nao deve nascer como pagina de texto corrida.

## Estrutura

### Bloco 1 - Header do treino
Conteudo:
1. `WOD de hoje`
2. horario/aula
3. coach
4. status da aula

### Bloco 2 - Cards de blocos
Cada bloco deve ser um card separado.

Tipos comuns:
1. aquecimento
2. forca
3. skill
4. metcon
5. cooldown

### Bloco 3 - Card de recomendacao por movimento
Quando houver `% RM`, mostrar:
1. nome do movimento
2. formula
3. carga recomendada
4. base da conta

Exemplo:
- `Baseado no seu RM atual de 100 kg`

### Bloco 4 - Acoes rapidas
1. `Ver RM`
2. `Voltar para grade`

### Wireframe textual

```text
[Topbar]

WOD de hoje
Cross Training - 19:00

[Bloco]
Aquecimento
3 rounds
...

[Bloco]
Forca
Deadlift
5 x 10 @ 70% do RM

[Card de recomendacao]
Seu peso recomendado
70 kg
Baseado no seu RM atual de 100 kg

[Bloco]
Metcon
12 min AMRAP
...

[Atalhos]
Ver RM | Voltar para grade
```

### CTA principal
Nao precisa de botao gigante se o treino ja estiver aberto.

O CTA principal pode ser a propria leitura do treino.

### CTA secundario
`Ver RM`

### Regras de UX
1. cada bloco deve caber visualmente como card
2. o movimento principal precisa aparecer acima da dobra em muitos casos
3. o peso recomendado nao pode ficar escondido no final

### Failure check
Se o aluno tiver que fazer conta mental no meio do treino quando o sistema ja tem os dados, a tela falhou.

---

# 4. Wireframe - RM

## Papel da tela

`RM` e o cockpit de capacidade do aluno.

No inicio, precisa ser simples.

Nao precisa nascer como dashboard complexo.

## Estrutura

### Bloco 1 - Header
Conteudo:
1. titulo `RM`
2. subtitulo curto

Exemplo:
- `Seus records maximos`

### Bloco 2 - Lista de movimentos
Cada item mostra:
1. nome do movimento
2. valor do RM
3. unidade
4. data de atualizacao
5. CTA de editar

### Bloco 3 - CTA para adicionar movimento
1. `Adicionar RM`

### Bloco 4 - Explicacao curta
1. como isso ajuda no treino

Exemplo:
- `Seus RMs ajudam o app a sugerir a carga ideal quando o treino usa porcentagem.`

### Wireframe textual

```text
[Topbar]

RM
Seus records maximos

[Lista]
Deadlift
100 kg
Atualizado ha 12 dias
[Atualizar]

Back Squat
90 kg
Atualizado ha 8 dias
[Atualizar]

Snatch
55 kg
Atualizado ha 21 dias
[Atualizar]

[CTA]
Adicionar RM

[Card explicativo]
Seus RMs ajudam o app a sugerir a carga ideal quando o treino usa porcentagem.
```

### CTA principal
`Adicionar RM`

### CTA secundario
`Atualizar`

### Estado vazio
1. mensagem clara
2. CTA forte para primeiro RM

Exemplo:
- `Voce ainda nao registrou seus RMs.`
- `[Registrar primeiro RM]`

### Failure check
Se a tela de RM parecer complicada antes de ter valor pratico, a tela falhou.

---

# 5. Estados especiais transversais

## Aguardando aprovacao
1. bloquear fluxo normal
2. CTA para entender o proximo passo

## Suspenso financeiro
1. mensagem clara
2. CTA para regularizar ou falar com o box

## Sem box ativo
1. CTA para entrar com convite
2. CTA para falar com o box

Esses estados continuam acima da navegacao de produto.

Em linguagem simples:
se a pessoa ainda nao entrou na escola, nao adianta mostrar a licao.

---

# 6. Ordem de implementacao recomendada

## Passo 1
Codar a shell e o `Inicio` em modo Grade

## Passo 2
Codar `Grade`

## Passo 3
Codar `WOD` em leitura simples

## Passo 4
Codar `RM` simples

## Passo 5
Ligar `Inicio` ao estado `wod_active`

## Passo 6
Ligar `WOD` ao motor de recomendacao por RM

---

# 7. Checks finais

Antes de codar, confirmar:

1. `Inicio` e contexto, nao destino fixo
2. `Grade` resolve a chegada
3. `WOD` resolve a execucao
4. `RM` e fundacao de personalizacao
5. mobile continua limpo
6. nenhuma logica de negocio vai parar dentro do template

# Resumo curto

O mapa visual fica assim:

1. `Inicio` decide o momento
2. `Grade` guia a rotina
3. `WOD` guia o treino
4. `RM` guia a carga

Se fizermos isso nessa ordem, a interface nasce como produto.

Nao como colecao de telas.
