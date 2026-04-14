<!--
ARQUIVO: plano de setup real do primeiro box piloto Endorfina Cross.

TIPO DE DOCUMENTO:
- plano operacional preenchido

AUTORIDADE:
- alta para o onboarding do primeiro box real

DOCUMENTOS IRMAOS:
- [first-box-pilot-intake-sheet.md](first-box-pilot-intake-sheet.md)
- [first-box-system-setup-checklist.md](first-box-system-setup-checklist.md)
- [first-box-onboarding-runbook.md](first-box-onboarding-runbook.md)
- [first-box-production-execution-checklist.md](first-box-production-execution-checklist.md)
- [phase1-closed-beta-operations-matrix.md](phase1-closed-beta-operations-matrix.md)

QUANDO USAR:
- para preparar a implantacao real da Endorfina Cross
- para saber o que ja esta definido e o que ainda bloqueia o dia 1
- para conduzir o setup dentro do OctoBox sem improviso

PONTOS CRITICOS:
- este plano e especifico para o primeiro box real conhecido hoje
- ele nao substitui a ficha de coleta; ele traduz a ficha em ordem de execucao
- campos criticos nao preenchidos continuam sendo bloqueadores do onboarding
-->

# Plano de setup real do primeiro box - Endorfina Cross

## Objetivo

Transformar a ficha de coleta da Endorfina Cross em um plano executavel de onboarding do primeiro box real.

Em linguagem simples: a ficha e a lista de compras. Este documento e a ordem de como os moveis entram na casa.

## Identificacao do box

- nome do box: `Endorfina Cross`
- cidade/estado: `Guarulhos, Sao Paulo`
- responsavel principal: `Fernando`
- email principal: `endorfinacross@gmail.com`
- data registrada na ficha: `13/03/2026`

## Escopo combinado do piloto

Entrar apenas com:

1. login e papeis
2. dashboard
3. alunos
4. cadastro e edicao leve
5. cobranca curta
6. grade em leitura
7. Recepcao

Status hoje:

- escopo curto: `aprovado`
- aceite formal do escopo: `aprovado`

Bloqueador:

1. nao ampliar o escopo curto no dia do onboarding sem novo aceite formal

## O que ja esta pronto no sistema

### Infra e homologacao

1. homologacao local PostgreSQL validada
2. restore PostgreSQL real provado
3. `owner`, `manager` e `reception` respondendo `200` no smoke da homologacao restaurada
4. runtime boundary e fallback de Fase 1 validados

### Aplicacao

1. `bootstrap_roles` funciona
2. grupos formais existem:
   - `Owner`
   - `DEV`
   - `Manager`
   - `Recepcao`
   - `Coach`
   - `honeypot`

Leitura:

1. a casa ja tem estrutura
2. agora estamos mobiliando a Endorfina Cross dentro dela

## Dados ja definidos da Endorfina Cross

### Pessoas do box

#### Owner

- nome: `Fernando`
- email: `endorfinacross@gmail.com`

#### Manager

- nome: `Mayara`
- email: `mayaraal@gmail.com`

#### Recepcao

- usuario dedicado: `nao definido ainda`
- cobertura contingencial: `Fernando` como `Owner` no dia 1

#### Coach

- nome: `Renan`
- email: `renanfulas@outlook.com`

### Planos principais

1. `Iniciante`
   - valor: `180`
   - ciclo: `monthly`
   - sessoes por semana: `2`
   - descricao: `Iniciante 2x semana`

2. `Scaled`
   - valor: `200`
   - ciclo: `monthly`
   - sessoes por semana: `3`
   - descricao: `Scaled`

3. `RX`
   - valor: `220`
   - ciclo: `monthly`
   - sessoes por semana: `6`
   - descricao: `RX`

### Alunos

- rota escolhida: `cadastro manual inicial`
- quantidade estimada: `100`

### Cobranca curta

- principal metodo de pagamento: `pix e cartao`
- parcelamento: `nao`
- cobranca recorrente: `pendente de confirmacao`

## Bloqueadores atuais do setup real

1. `usuario oficial de Recepcao` ainda nao definido para o pos-piloto
2. `grade essencial` ainda nao foi preenchida no sistema
3. `horario do onboarding` ainda nao foi executado
4. `Fernando` sera o unico participante confirmado do onboarding

Em linguagem simples: a cozinha ja existe, mas ainda faltam decidir quem cozinha, que horas abre e quais panelas vao para o fogao.

## Decisoes que precisamos fechar antes do dia 1

### 1. Recepcao

Escolher uma das duas:

1. `recomendado`: definir o usuario oficial de Recepcao
2. `contingencia`: registrar por escrito que o fluxo sera coberto por `Fernando`

Regra:

1. nao inventar um usuario ficticio de Recepcao so para preencher tabela

Status decidido hoje:

1. `Recepcao do dia 1`: `Fernando` em contingencia

### 2. Grade essencial

Precisamos de pelo menos 3 aulas reais descritas com:

1. nome da aula
2. dia da semana
3. horario
4. coach responsavel

### 3. Janela do onboarding

Fechar:

1. data definitiva
2. horario definitivo
3. quem participa da validacao final

Status decidido hoje:

1. data: `15/04/2026`
2. horario: `15:00`
3. participante principal: `Fernando`

## Setup real do dia 1

### Etapa 1. Runtime e health

Confirmar:

1. `BOX_RUNTIME_SLUG` do box piloto
2. `/api/v1/health/` com `status=ok`
3. `runtime_slug` coerente
4. `runtime_namespace` coerente

Aceite:

1. o box piloto precisa entrar na casa certa antes de qualquer usuario entrar

### Etapa 2. Criar usuarios reais

Criar na ordem:

1. `Fernando` como `Owner`
2. `Mayara` como `Manager`
3. `Recepcao` oficial, se ja existir
4. `Renan` como `Coach`

Checklist por usuario:

1. usuario criado
2. email correto
3. grupo correto
4. login testado
5. redirecionamento testado

### Etapa 3. Cadastrar os 3 planos da Endorfina

Cadastrar exatamente:

1. `Iniciante` - `R$ 180` - `monthly` - `2x semana`
2. `Scaled` - `R$ 200` - `monthly` - `3x semana`
3. `RX` - `R$ 220` - `monthly` - `6x semana`

Aceite:

1. os tres planos aparecem e podem ser usados nas matriculas

### Etapa 4. Carregar a base inicial de alunos

Como a rota escolhida hoje e `cadastro manual inicial`, fazer:

1. comecar pelos alunos ativos mais importantes
2. priorizar alunos que precisam de cobranca ou atendimento no dia 1
3. garantir nome completo e WhatsApp corretos

Meta do dia 1:

1. nao precisa entrar os `100` alunos
2. precisa entrar o suficiente para o box sentir o sistema funcionando sem medo

Meta recomendada:

1. `10 a 20 alunos` mais importantes primeiro

### Etapa 5. Montar a grade essencial

Cadastrar no minimo:

1. `3 aulas reais`

Aceite:

1. a grade abre em `/grade-aulas/`
2. a leitura aparece para `Owner`, `Manager`, `Recepcao` e `Coach`

### Etapa 6. Testar Recepcao real

Executar:

1. entrar em `/operacao/recepcao/`
2. localizar aluno
3. enxergar grade em leitura
4. tratar uma cobranca curta

Se ainda nao houver usuario dedicado:

1. registrar por escrito a contingencia
2. testar com o papel que vai cobrir de verdade
3. na Endorfina Cross, testar com `Fernando`

### Etapa 7. Smoke por papel

#### Owner

1. `/dashboard/`
2. `/alunos/`
3. `/grade-aulas/`
4. `/operacao/owner/`

#### Manager

1. `/dashboard/`
2. `/alunos/`
3. `/operacao/manager/`

#### Recepcao

1. `/operacao/recepcao/`
2. `/alunos/`
3. cobranca curta

#### Coach

1. `/operacao/coach/`
2. `/grade-aulas/`

## Critério de pronto da Endorfina Cross

A Endorfina Cross so entra em uso piloto real quando:

1. `Fernando` entra como `Owner`
2. `Mayara` entra como `Manager`
3. o papel que vai cobrir `Recepcao` esta definido e testado
4. os 3 planos principais existem
5. a grade essencial tem pelo menos 3 aulas
6. existe uma base inicial minima de alunos utilizavel
7. o fluxo curto de Recepcao funciona
8. Fernando confirma o aceite do escopo curto

## Risco de debito tecnico se improvisarmos

1. entrar sem `Recepcao` definida empurra confusao operacional para o dia 1
   na Endorfina isso esta coberto por contingencia com `Fernando`, mas so para o piloto curto
2. entrar sem `grade essencial` faz o sistema parecer incompleto mesmo quando o backend esta certo
3. entrar sem `aceite do escopo` faz cada demanda virar promessa implícita
4. tentar cadastrar `100 alunos` no mesmo dia pode transformar onboarding em exaustao e mascarar bugs reais

Em linguagem simples: se a gente tentar encher a piscina, montar o parquinho e fazer festa no mesmo minuto, ninguem sabe mais se a agua estava limpa ou se o escorregador quebrou.

## Menor caminho de execucao

### Agora

1. confirmar `aceite do escopo curto`
2. manter `Fernando` como contingencia formal da `Recepcao`
3. preencher as aulas reais da grade
4. onboarding fechado para `15/04/2026 às 15:00`

### No dia do onboarding

1. validar runtime e health
2. criar usuarios
3. cadastrar 3 planos
4. cadastrar de `10 a 20 alunos` prioritarios
5. montar as aulas reais informadas
6. testar Recepcao com `Fernando`
7. rodar smoke por papel

### Depois

1. ampliar a base de alunos
2. ampliar grade
3. remover contingencias
4. entrar no war room dos primeiros dias

## Formula curta

Para a Endorfina Cross entrar bem, o objetivo nao e colocar tudo para dentro.

E colocar o suficiente, na ordem certa, para Fernando sentir:

1. a casa esta pronta
2. as pessoas conseguem entrar
3. os alunos aparecem
4. a grade existe
5. a Recepcao resolve o essencial
