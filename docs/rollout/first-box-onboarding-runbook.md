<!--
ARQUIVO: runbook operacional do primeiro box piloto.

TIPO DE DOCUMENTO:
- runbook operacional de onboarding

AUTORIDADE:
- alta para implantacao do primeiro box

DOCUMENTO PAI:
- [first-box-rollout-plan.md](first-box-rollout-plan.md)

QUANDO USAR:
- quando a duvida for como preparar, configurar e validar a entrada do primeiro box no OctoBox sem improviso

POR QUE ELE EXISTE:
- transforma a fase de onboarding assistido em uma sequencia curta, repetivel e auditavel.
- reduz o risco de esquecer configuracao critica no primeiro cliente piloto.

O QUE ESTE ARQUIVO FAZ:
1. define o preparo minimo antes do box entrar.
2. organiza o dia de configuracao do box.
3. registra smoke tests operacionais do primeiro dia.

PONTOS CRITICOS:
- este runbook serve para o primeiro box piloto, nao para rollout em massa.
- qualquer divergencia entre operacao real e escopo do piloto deve ser registrada antes de prosseguir.
-->

# Runbook do primeiro box piloto

## Objetivo

Colocar o primeiro box para rodar no OctoBox com escopo controlado, acompanhamento proximo e validacao de uso real no mesmo dia.

## Escopo operacional do piloto

O primeiro box deve entrar apenas com o pacote minimo ja definido no rollout:

1. login e papeis
2. dashboard
3. alunos
4. cadastro e edicao leve
5. cobranca curta
6. grade de aulas em leitura
7. Recepcao

Nao ampliar escopo no meio do onboarding.

## Preparo antes do dia de implantacao

Antes de comecar, preencher a ficha de coleta em [first-box-pilot-intake-sheet.md](first-box-pilot-intake-sheet.md).

Se o box piloto atual for a Endorfina Cross, usar o plano preenchido em [first-box-endorfina-cross-setup-plan.md](first-box-endorfina-cross-setup-plan.md) como trilho operacional do dia 1.

No dia da implantacao, executar o setup interno seguindo [first-box-system-setup-checklist.md](first-box-system-setup-checklist.md).

### 1. Validar homologacao

Antes de envolver o box, confirmar:

1. deploy publicado e estavel
2. login funcionando
3. `/api/v1/health/` respondendo OK
4. dashboard carregando com CSS
5. [bootstrap_roles.py](../../boxcore/management/commands/bootstrap_roles.py) executado
6. superuser criado
7. backup inicial do banco gerado

### 2. Coletar dados minimos do box

Chegar no dia da implantacao com isso em maos:

1. nome oficial do box
2. responsavel principal
3. lista de pessoas que vao operar o sistema
4. papeis esperados por pessoa
5. lista inicial de planos
6. base inicial de alunos ou confirmacao de cadastro manual
7. grade essencial da semana

Se a carga inicial for por CSV, usar [first-box-student-import-template.csv](first-box-student-import-template.csv) como modelo da base.

### 3. Congelar combinados do piloto

Explicar antes:

1. o piloto e assistido
2. o escopo inicial e propositalmente curto
3. ajustes pequenos entram rapido
4. customizacao grande nao entra no primeiro ciclo

## Papéis que devem existir no primeiro box

Papéis recomendados no piloto:

1. um responsavel Owner
2. um operador Manager, se existir
3. um operador Recepcao, sempre que o piloto for usar o fluxo oficial de balcao
4. um ou mais Coach, se a rotina exigir

Evitar criar usuarios sem papel definido.

## Sequencia de implantacao do box

### Etapa 1. Criar usuarios e vincular grupos

Checklist:

1. criar usuario Owner do box
2. criar usuario Manager quando existir
3. criar usuario Recepcao quando o piloto for usar o fluxo com operador dedicado
4. criar usuario Coach quando existir
5. validar login individual de pelo menos um usuario por papel ativo no piloto

### Etapa 2. Cadastrar planos principais

Cadastrar apenas o necessario para rodar:

1. nome do plano
2. valor
3. regra de recorrencia ou parcelamento mais comum
4. condicoes comerciais essenciais

Evitar cadastrar variacoes raras no primeiro dia.

### Etapa 3. Carregar base inicial de alunos

Escolher uma das duas rotas:

1. importacao por CSV, se a base estiver minimamente limpa
2. cadastro manual dos alunos ativos mais importantes

Comando de importacao por CSV:

```powershell
& "c:/Users/renan/OneDrive/Documents/Integração PY/.venv/Scripts/python.exe" manage.py import_students_csv caminho-do-arquivo.csv --delimiter ";"
```

Validacoes obrigatorias:

1. nomes aparecem corretamente em [templates/catalog/students.html](../../templates/catalog/students.html)
2. telefone principal veio coerente
3. buscas por nome e telefone funcionam

### Etapa 4. Montar grade essencial

Cadastrar apenas a grade que o box precisa usar agora.

Checklist:

1. aulas principais da semana
2. horarios reais
3. coach vinculado quando aplicavel
4. revisar a leitura em [templates/catalog/class-grid.html](../../templates/catalog/class-grid.html)
5. revisar a leitura operacional em [templates/operations/reception.html](../../templates/operations/reception.html)

### Etapa 5. Validar fluxo de atendimento

Testar com um aluno real ou de homologacao:

1. login
2. abrir dashboard
3. localizar aluno
4. editar aluno
5. abrir Recepcao em `/operacao/recepcao/`
6. abrir grade em leitura
7. validar cobranca curta

### Etapa 6. Validar pagamento curto

Executar pelo menos um teste de fluxo:

1. localizar um pagamento pendente
2. abrir a acao de pagamento na Recepcao
3. salvar ajuste curto ou marcar como pago
4. conferir reflexo na ficha do aluno

## Smoke test do dia 1

Antes de considerar o box apto para uso real, confirmar:

1. Owner consegue logar
2. Manager consegue logar, se existir
3. Recepcao consegue logar, quando houver usuario dedicado para esse fluxo
4. Coach consegue logar, se existir
5. dashboard abre
6. alunos abre
7. novo aluno abre
8. grade abre
9. Recepcao abre
10. uma acao curta de pagamento funciona

## O que explicar para o box no primeiro dia

Explicar de forma curta:

1. onde entra cada papel
2. o que a Recepcao resolve
3. o que ainda nao faz parte do piloto
4. para onde mandar bug ou duvida
5. qual o prazo esperado de resposta

## Registro minimo da implantacao

Ao fim do onboarding, registrar:

1. nome do box
2. data da implantacao
3. usuarios criados
4. planos cadastrados
5. quantidade de alunos importados ou cadastrados
6. grade base configurada
7. pendencias abertas

## Criterio de pronto do primeiro box

O primeiro box so entra em uso piloto real quando:

1. os usuarios principais conseguem entrar
2. a operacao minima roda sem admin bruto
3. o fluxo oficial de Recepcao consegue localizar aluno, enxergar aula e tratar cobranca curta; se houver contingencia por Owner ou Manager, isso precisa estar formalmente registrado
4. existe um canal de suporte ativo para os primeiros 7 a 14 dias

## Formula curta

O primeiro box nao precisa entrar com tudo.

Ele precisa entrar com o suficiente para funcionar sem medo.
