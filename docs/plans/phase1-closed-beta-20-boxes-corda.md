<!--
ARQUIVO: C.O.R.D.A. operacional da Fase 1 do OctoBox para beta fechado ate 20 boxes.

TIPO DE DOCUMENTO:
- prompt operacional reutilizavel

AUTORIDADE:
- alta para execucao da Fase 1

DOCUMENTOS IRMAOS:
- [scale-transition-20-100-open-multitenancy-plan.md](scale-transition-20-100-open-multitenancy-plan.md)
- [unit-cascade-architecture-plan.md](unit-cascade-architecture-plan.md)
- [../rollout/first-box-production-execution-checklist.md](../rollout/first-box-production-execution-checklist.md)
- [../rollout/homologation-deploy-checklist.md](../rollout/homologation-deploy-checklist.md)
- [../rollout/beta-internal-release-gate.md](../rollout/beta-internal-release-gate.md)

QUANDO USAR:
- quando a tarefa for fechar a Fase 1 de forma executavel
- quando precisarmos revisar o que ja existe, o que esta parcial e o que bloqueia o primeiro box
- quando quisermos orientar um agente ou um engenheiro a terminar o beta fechado sem inflar escopo

POR QUE ELE EXISTE:
- evita que a Fase 1 vire conversa abstrata de arquitetura sem fechamento operacional.
- transforma o plano de escala em prompt de execucao.
- explicita os `failure checks` que invalidam o go-live.

O QUE ESTE ARQUIVO FAZ:
1. consolida o contexto oficial da Fase 1.
2. define o objetivo, os riscos e a direcao tecnica.
3. fornece um prompt reutilizavel em formato C.O.R.D.A.
4. registra checks de falha que impedem respostas bonitas e frouxas.

PONTOS CRITICOS:
- este documento nao autoriza abrir o primeiro box sem restore testado.
- este documento nao autoriza owner hub, multitenancy aberto ou hop extra no request.
- este documento deve seguir o runtime atual como verdade quando houver conflito com a documentacao.
-->

# C.O.R.D.A. - Fase 1 ate 20 boxes

## C - Contexto

O OctoBox esta na Fase 1 do plano oficial de escala:

1. beta fechado
2. ate 20 boxes
3. 1 servidor
4. isolamento forte

Baseline operacional desta fase:

1. 6 funcionarios por box
2. 200 alunos por box
3. 120 funcionarios cadastrados
4. 4000 alunos
5. picos de uso entre `06:00-10:00` e `17:00-21:00`
6. distribuicao de uso: `35%` de manha e `65%` a noite

Superficies mais quentes:

1. `reception`
2. `manager`
3. `finance hot paths`

Superficie mais fria:

1. `owner`

O runtime atual ja possui fundamentos importantes:

1. `intent_id` nos fluxos criticos
2. `snapshot_version` em `manager`, `reception` e `owner`
3. fallback por versao nas superficies quentes
4. `BOX_RUNTIME_SLUG` e `runtime_namespace`
5. checklist executavel do primeiro box em [../rollout/first-box-production-execution-checklist.md](../rollout/first-box-production-execution-checklist.md)

Em linguagem simples:

1. a casa ja tem parede e encanamento
2. esta faltando garantir que a chave abre, a luz volta e a mangueira de incendio funciona

## O - Objetivo

Fechar a Fase 1 para operar do primeiro box ate 20 boxes em 1 servidor, com:

1. isolamento forte
2. custo baixo
3. recuperacao simples
4. confiabilidade suficiente para o primeiro go-live
5. base preparada para a Fase 2 sem reescrever o produto

Sucesso significa:

1. o ambiente sobe e responde
2. o runtime sabe qual box/celula representa
3. os usuarios do box conseguem operar o pacote minimo
4. existe backup, rollback e suporte para o primeiro susto
5. `manager`, `reception` e `owner` continuam respirando quando o barramento quente falha

## R - Riscos

### 1. Risco de beta bonito e fraco

Se abrirmos o primeiro box sem restore testado, rollback ensaiado e smoke real:

1. o beta parece pronto
2. mas falha no primeiro susto de producao

### 2. Risco de isolamento pela metade

Se o isolamento parar em cache e nao chegar em logs, exports, storage e operacao:

1. a casa tem parede
2. mas a fiação continua cruzando por baixo do piso

### 3. Risco de realtime fragil

Se o sistema depender so do barramento quente:

1. a tela parece morta
2. mesmo quando o backend esta certo

### 4. Risco de debito tecnico perigoso

Se tentarmos fechar a Fase 1 criando:

1. owner hub cedo demais
2. multitenancy aberto cedo demais
3. nova arquitetura gigante

vamos pagar custo de shopping para abrir uma mercearia.

## D - Direcao

### Regra principal

Terminar a Fase 1 com o menor passo de maior ROI.

### O que respeitar

1. `intent_id` e `snapshot_version` ja existem
2. `runtime boundary` ja existe
3. os docs de rollout ja existem
4. o runtime atual tem prioridade sobre a narrativa documental quando houver conflito

### O que NAO fazer

1. nao criar owner hub completo
2. nao criar multitenancy aberto
3. nao criar hop extra no request
4. nao transformar `AuditEvent` em read model final
5. nao duplicar documentacao sem necessidade

### O que precisa ser tratado como item de primeira classe

1. `restore`
2. `rollback`
3. `BOX_RUNTIME_SLUG`
4. `/api/v1/health/`
5. fallback operacional de `manager`, `reception` e `owner`

## A - Acoes

### Onda 1 - Auditoria real da Fase 1

Classificar tudo em:

1. `ja implementado`
2. `parcial`
3. `faltando`
4. `bloqueador`

### Onda 2 - Fechar os bloqueadores do primeiro box

No minimo:

1. restore testado
2. rollback ensaiado
3. runtime boundary validada
4. smoke funcional das superficies quentes
5. checklist executavel do primeiro box rodado

### Onda 3 - Go-live assistido

1. rodar o primeiro box com escopo congelado
2. observar os primeiros 7 a 14 dias
3. corrigir o que trava a rotina curta

---

## Prompt Operacional Reutilizavel

```text
Voce vai atuar como arquiteto de rollout, operacao e confiabilidade do OctoBox na Fase 1.

Missao principal:
fechar a Fase 1 do beta fechado para operar do primeiro box ate 20 boxes em 1 servidor, com isolamento forte, sem abrir debito tecnico perigoso para a Fase 2.

Contexto oficial:
- data-base: 2026-04-13
- topologia alvo da Fase 1: 1 servidor, isolamento forte por box, beta fechado
- baseline operacional:
  - ate 20 boxes
  - 6 funcionarios por box
  - 200 alunos por box
  - 120 funcionarios cadastrados
  - 4000 alunos
  - picos de uso: 06:00-10:00 e 17:00-21:00
  - distribuicao de uso: 35 por cento manha e 65 por cento noite
- roles com maior pressao:
  - recepcao
  - manager
- superficie mais fria:
  - owner

Estado atual que deve ser respeitado:
- intent_id ja existe nos fluxos criticos
- snapshot_version ja existe em manager, reception e owner
- manager, reception e owner ja possuem fallback por version no frontend
- BOX_RUNTIME_SLUG e runtime_namespace ja existem no runtime atual
- existe checklist executavel do primeiro box em docs/rollout/first-box-production-execution-checklist.md
- existe checklist de homologacao e runbooks relacionados em docs/rollout/

Objetivo:
produzir e executar um fechamento real da Fase 1, separando o que ja esta pronto, o que esta parcial, o que falta, o que bloqueia o primeiro box e o que deve ser adiado para nao inflar escopo.

Regras obrigatorias:
- nao criar nova arquitetura grande
- nao criar owner hub completo
- nao criar multitenancy aberto
- nao criar hop extra no request
- nao transformar AuditEvent no read model final
- nao abrir o primeiro box sem restore testado
- nao abrir o primeiro box sem rollback minimamente ensaiado
- nao abrir o primeiro box sem validar runtime boundary via healthcheck
- nao abrir o primeiro box sem smoke funcional das superficies quentes
- nao duplicar documentacao sem motivo se um doc existente puder ser promovido a fonte oficial

Definicao de Fase 1 pronta:
a Fase 1 so pode ser considerada pronta quando:
1. o ambiente sobe e responde
2. o runtime sabe qual box/celula representa
3. os usuarios do box conseguem operar o pacote minimo
4. existe backup, rollback e suporte para o primeiro susto
5. manager, reception e owner continuam respirando quando o barramento quente falha
6. o time consegue explicar claramente o que entra e o que nao entra no piloto

Escopo da analise:
1. revisar a Fase 1 do plano de escala
2. revisar o checklist executavel do primeiro box
3. mapear lacunas entre documentacao e runtime atual
4. organizar a execucao em ondas curtas ate o go-live do primeiro box
5. registrar bloqueadores reais
6. distinguir debito tecnico controlado de debito tecnico perigoso

Formato de saida obrigatorio:
1. Diagnostico da Fase 1
- dividir em:
  - ja implementado
  - parcial
  - faltando
  - bloqueador
2. Checklist executavel consolidado
- listar apenas a ordem de execucao real
- cada item deve ser verificavel
3. Ondas de execucao
- onda 1: antes do primeiro box
- onda 2: dia do primeiro box
- onda 3: primeiros 7 a 14 dias
4. Failure checks
- listar o que invalida o go-live imediatamente
5. Debito tecnico
- dividir em:
  - aceitavel agora
  - perigoso agora
6. Gate final
- responder com:
  - pode abrir
  - pode abrir com ressalvas
  - nao pode abrir ainda
- justificar em no maximo 5 pontos

Quality bar:
- priorizar clareza operacional acima de teoria
- tratar runtime boundary, restore, rollback e fallback de realtime como itens de primeira classe
- se algo ja estiver implementado, nao pedir para reinventar
- se algo estiver parcial, explicar exatamente o que falta para ficar pronto
- se uma lacuna puder derrubar o primeiro box, classificar como bloqueador

Fallback behavior:
- se houver incerteza entre documentacao e runtime, assumir o runtime como verdade atual e apontar a divergencia
- se faltar uma peca para fechar a Fase 1, propor o menor passo com maior ROI
```

---

## Failure checks

Se qualquer resposta falhar em um destes pontos, o plano de execucao esta frouxo:

1. nao cita `restore`
2. nao cita `rollback`
3. nao cita `BOX_RUNTIME_SLUG`
4. nao cita `/api/v1/health/`
5. nao trata `manager`, `reception` e `owner` separadamente
6. pede arquitetura nova grande para fechar a Fase 1
7. nao termina com gate claro de liberacao

---

## O que ainda faltava e entrou neste C.O.R.D.A.

1. `restore testado` como bloqueador real
2. `rollback ensaiado` como bloqueador real
3. `runtime boundary` como condicao de aceite
4. fallback de `manager`, `reception` e `owner` como item de producao
5. regra explicita de nao reinventar o que ja existe
6. runtime como verdade em caso de conflito com docs

## Formula curta

Este C.O.R.D.A. existe para impedir um erro comum:

1. achar que Fase 1 pronta e so deploy bonito

Quando, na verdade, Fase 1 pronta significa:

1. sobe
2. respira
3. recupera
4. e o primeiro box nao entra no escuro
