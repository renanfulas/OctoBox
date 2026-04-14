<!--
ARQUIVO: checklist operacional do onboarding da Endorfina Cross no dia 15/04/2026.

TIPO DE DOCUMENTO:
- checklist operacional executavel

AUTORIDADE:
- alta para o dia do onboarding do primeiro box real

DOCUMENTOS IRMAOS:
- [first-box-endorfina-cross-setup-plan.md](first-box-endorfina-cross-setup-plan.md)
- [first-box-onboarding-runbook.md](first-box-onboarding-runbook.md)
- [first-box-system-setup-checklist.md](first-box-system-setup-checklist.md)
- [first-box-production-execution-checklist.md](first-box-production-execution-checklist.md)

QUANDO USAR:
- no onboarding real da Endorfina Cross em 15/04/2026 as 15:00
- para conduzir a implantacao em ordem curta e verificavel

PONTOS CRITICOS:
- este checklist e do dia da operacao, nao do planejamento
- se um gate critico falhar, parar e corrigir antes de continuar
- nao ampliar o escopo curto no meio da sessao
-->

# Checklist operacional do onboarding - Endorfina Cross - 15/04/2026 15:00

## Janela oficial

- box: `Endorfina Cross`
- data: `15/04/2026`
- horario: `15:00`
- participante principal: `Fernando`
- cobertura contingencial de Recepcao no piloto curto: `Fernando`

Em linguagem simples: este documento e a folha do piloto no painel do aviao. A ideia nao e improvisar; e seguir a ordem para o voo sair reto.

## Gate de inicio

Antes de abrir a sessao com Fernando, confirmar:

1. homologacao PostgreSQL local ja foi validada
2. `/api/v1/health/` responde `status=ok`
3. login esta abrindo
4. o operador que vai executar o onboarding tem acesso de admin ou equivalente
5. o escopo curto continua congelado

Se qualquer item acima falhar:

1. nao iniciar onboarding com o box
2. corrigir o bloqueio
3. recomecar a partir do Gate de inicio

## Ordem de execucao do dia

### Bloco 1 - abertura da sessao - 15:00 a 15:10

Objetivo:

1. alinhar expectativa
2. lembrar o que entra hoje
3. evitar promessas implicitas

Checklist:

1. confirmar com Fernando que o foco hoje e:
   - login e papeis
   - dashboard
   - alunos
   - cadastro e edicao leve
   - cobranca curta
   - grade em leitura
   - Recepcao
2. registrar que `Recepcao` no dia 1 ficara em contingencia com `Fernando`
3. avisar que o objetivo nao e cadastrar os `100 alunos` no mesmo dia
4. avisar que a meta do dia e sair com o suficiente para operar sem medo

Aceite do bloco:

1. Fernando confirma o escopo curto
2. Fernando confirma que a contingencia de Recepcao esta clara

### Bloco 2 - runtime e acesso base - 15:10 a 15:20

Objetivo:

1. provar que a casa certa esta de pe

Checklist:

1. abrir `/api/v1/health/`
2. verificar:
   - `status=ok`
   - `runtime_slug` coerente
   - `runtime_namespace` coerente
3. abrir `/login/`
4. abrir `/dashboard/`
5. abrir `/alunos/`
6. abrir `/grade-aulas/`

Failure check:

1. se `health` nao responder ou responder runtime errado, parar
2. se login ou dashboard nao abrirem, parar

### Bloco 3 - usuarios reais - 15:20 a 15:35

Objetivo:

1. colocar as pessoas certas dentro da casa

Usuarios do piloto:

1. `Fernando` - `Owner`
2. `Mayara` - `Manager`
3. `Renan` - `Coach`

Checklist:

1. confirmar usuario `Fernando` criado com email `endorfinacross@gmail.com`
2. confirmar usuario `Mayara` criado com email `mayaraal@gmail.com`
3. confirmar usuario `Renan` criado com email `renanfulas@outlook.com`
4. validar grupo correto de cada um
5. testar login de `Fernando`
6. se houver tempo e acesso, testar login de `Mayara`

Failure check:

1. se `Fernando` nao entrar, parar
2. se o grupo de `Fernando` nao for `Owner`, corrigir antes de seguir

### Bloco 4 - planos - 15:35 a 15:50

Objetivo:

1. colocar os 3 produtos comerciais basicos da Endorfina dentro do sistema

Checklist:

1. cadastrar ou validar `Iniciante` - `R$ 180` - `monthly` - `2x semana`
2. cadastrar ou validar `Scaled` - `R$ 200` - `monthly` - `3x semana`
3. cadastrar ou validar `RX` - `R$ 220` - `monthly` - `6x semana`
4. confirmar que os 3 aparecem e podem ser usados na matricula

Failure check:

1. se algum plano nao salvar, corrigir antes de passar para alunos

### Bloco 5 - base inicial de alunos - 15:50 a 16:20

Objetivo:

1. fazer o box sentir o sistema vivo sem tentar engolir o oceano

Regra:

1. cadastrar primeiro `10 a 20 alunos` prioritarios
2. priorizar quem precisa de cobranca ou atendimento mais cedo

Checklist:

1. cadastrar os primeiros alunos prioritarios
2. validar nome completo
3. validar WhatsApp
4. validar busca por nome
5. validar busca por telefone
6. validar edicao leve de pelo menos 1 aluno

Failure check:

1. se o aluno nao aparecer em `/alunos/`, parar
2. se busca ou edicao falharem, parar

### Bloco 6 - grade essencial - 16:20 a 16:40

Objetivo:

1. colocar o quadro de aulas minimamente fiel ao box

Checklist de cadastro:

1. `Segunda, quarta e sexta`
   - `Cross 06:00` - `Renan`
   - `Cross 07:00` - `Renan`
   - `Cross 08:00` - `Renan`
2. `Terca e quinta`
   - `Cross 07:00` - `Renan`
   - `Cross 08:00` - `Renan`
3. `Terca, quinta e sexta`
   - `Cross 17:00` - `Eric`
   - `Cross 18:00` - `Eric`
   - `Cross 19:00` - `Eric`
   - `Cross 20:00` - `Eric`
4. `Segunda e quarta`
   - `Cross 17:00` - `Thiago ou Fernando`
   - `Cross 18:00` - `Thiago ou Fernando`
   - `Cross 19:00` - `Thiago ou Fernando`
   - `Cross 20:00` - `Thiago ou Fernando`

Checklist de validacao:

1. abrir `/grade-aulas/`
2. confirmar que a leitura da grade aparece
3. confirmar que a grade e visivel para o papel usado no onboarding

Failure check:

1. se a grade nao abrir ou ficar vazia mesmo com cadastro, parar

### Bloco 7 - Recepcao e cobranca curta - 16:40 a 17:00

Objetivo:

1. provar que o balcao minimo funciona

Checklist:

1. abrir `/operacao/recepcao/`
2. testar com `Fernando` na contingencia
3. localizar um aluno
4. enxergar a grade em leitura
5. localizar um caso simples de cobranca curta
6. salvar um ajuste curto ou marcar como pago, se houver dado suficiente
7. confirmar reflexo na ficha do aluno

Failure check:

1. se Recepcao nao abrir, parar
2. se nao localizar aluno, parar
3. se a cobranca curta quebrar com erro, parar

### Bloco 8 - smoke final e aceite - 17:00 a 17:15

Objetivo:

1. encerrar a sessao com clareza e sem zona cinzenta

Smoke minimo:

1. `Fernando` entra como `Owner`
2. dashboard abre
3. alunos abre
4. grade abre
5. Recepcao abre
6. os 3 planos existem
7. a base inicial de alunos esta utilizavel

Perguntas de aceite:

1. `Fernando, voce consegue enxergar o box funcionando no pacote curto de hoje?`
2. `Ficou claro o que entra hoje e o que fica para depois?`

Aceite do dia:

1. marcar `aprovado` se Fernando confirmar o pacote curto
2. marcar `com ressalvas` se houver algo contornavel mas nao bloqueante
3. marcar `nao aprovado` se houver falha em login, alunos, grade ou Recepcao

## Registro obrigatorio ao fim

Registrar no mesmo dia:

1. usuarios criados ou validados
2. planos criados ou validados
3. quantidade de alunos cadastrados
4. status da grade essencial
5. status da contingencia de Recepcao
6. pendencias abertas
7. aceite final do Fernando

## O que nao fazer no dia

1. nao tentar cadastrar os `100 alunos`
2. nao ampliar o escopo para financeiro profundo
3. nao inventar usuario falso de Recepcao
4. nao sair do onboarding sem aceite claro

## Formula curta

No dia 15/04 as 15:00, o objetivo nao e impressionar com volume.

E fazer Fernando sentir cinco coisas:

1. eu entro
2. meus planos existem
3. meus alunos aparecem
4. minha grade esta la
5. meu balcao resolve o essencial
