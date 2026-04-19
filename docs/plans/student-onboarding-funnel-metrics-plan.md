<!--
ARQUIVO: plano objetivo de metricas e funil do onboarding do aluno.

TIPO DE DOCUMENTO:
- plano de arquitetura + produto + observabilidade
- especificacao de metricas

AUTORIDADE:
- alta para a frente de metricas do onboarding do aluno

DOCUMENTOS PAIS:
- [intelligent-student-onboarding-plan.md](intelligent-student-onboarding-plan.md)
- [../architecture/octobox-architecture-model.md](../architecture/octobox-architecture-model.md)
- [../architecture/architecture-growth-plan.md](../architecture/architecture-growth-plan.md)

QUANDO USAR:
- quando a duvida for quais metricas o onboarding precisa publicar
- quando precisarmos construir um funil por jornada sem criar debito tecnico
- quando a equipe quiser transformar o painel de convites em painel de conversao

POR QUE ELE EXISTE:
- hoje o sistema ja sabe criar convite, abrir link e concluir entrada, mas ainda nao sabe ler o funil completo
- sem isso, operacao enxerga porta aberta, mas nao enxerga quantas pessoas chegaram, entraram e finalizaram
- este plano transforma o onboarding em uma esteira observavel, sem inventar uma segunda arquitetura paralela

O QUE ESTE ARQUIVO FAZ:
1. define nomes oficiais de eventos do funil
2. separa o funil por jornada
3. define onde cada evento deve disparar
4. define como o painel deve ler essas metricas
5. protege a arquitetura contra telemetria espalhada e inutil

PONTOS CRITICOS:
- evento de funil nao substitui verdade transacional
- `AuditEvent` pode sustentar a fase 1, mas nao deve virar analitico eterno pesado
- painel precisa mostrar progressao, nao apenas numeros frios
- metricas precisam respeitar a regra de nao pedir nem inferir alem do necessario
-->

# Plano - Student Onboarding Funnel Metrics

## 1. Resumo executivo

O onboarding do aluno ja tem 3 corredores oficiais:

1. `mass_box_invite`
2. `imported_lead_invite`
3. `registered_student_invite`

O que falta agora nao e mais o motor do fluxo.

O que falta e o painel de leitura do fluxo.

Em linguagem simples:

1. hoje sabemos que a porta existe
2. amanha precisamos saber quantas pessoas viram a porta
3. quantas giraram a macaneta
4. quantas entraram no corredor
5. quantas sentaram na sala

## 2. Contexto

Hoje a base ja possui:

1. `StudentAppInvitation`
2. `StudentBoxInviteLink`
3. callback OAuth em `student_identity`
4. wizard em `student_app`
5. painel operacional de convites
6. `AuditEvent` como trilha de fatos

O problema atual:

1. o painel ainda mostra mais `estado do convite` do que `conversao da jornada`
2. a operacao nao ve com clareza onde o aluno travou
3. owner e recepcao nao conseguem responder rapido:
   - quantos clicaram
   - quantos autenticaram
   - quantos terminaram

## 3. Objetivo

Publicar um funil enxuto e confiavel do onboarding do aluno, por jornada, sem criar uma camada pesada nem duplicar verdade transacional.

Sucesso significa:

1. o time consegue ler conversao por jornada
2. o painel mostra onde o aluno travou
3. a recepcao sabe quando atuar manualmente
4. o owner sabe se o corredor em massa esta convertendo ou vazando

## 4. Tese de arquitetura

### Regra principal

Usar a estrutura atual do predio:

1. `student_identity` continua dono dos fatos de invite, OAuth, delivery e membership
2. `student_app` continua dono dos fatos de wizard e perfil
3. o painel continua sendo montado por `presentation` + `page payload`
4. a leitura agregada nasce como `snapshot operacional`, nao como logica espalhada em template

### O que fazer agora

1. fase 1:
   usar `AuditEvent` e fatos transacionais existentes para publicar o funil

2. fase 2:
   extrair leitura para um `query/snapshot` proprio quando volume e uso justificarem

### O que nao fazer agora

1. nao criar nova tabela analitica prematura
2. nao empilhar contadores ad-hoc em varios models
3. nao jogar logica de funil dentro do template
4. nao chamar de conversao algo que e apenas clique

Analogia de crianca:

1. nao vamos construir outro predio so para contar quem entrou
2. primeiro usamos o porteiro e o livro de entrada
3. depois, se a fila crescer, colocamos catraca eletronica

## 5. Eventos oficiais do funil

### Nomeacao oficial

Padrao:

1. `student_onboarding.<journey>.<event>`

Exemplos:

1. `student_onboarding.mass_box_invite.landing_viewed`
2. `student_onboarding.mass_box_invite.oauth_started`
3. `student_onboarding.mass_box_invite.oauth_completed`
4. `student_onboarding.mass_box_invite.wizard_completed`
5. `student_onboarding.imported_lead_invite.whatsapp_handoff_opened`
6. `student_onboarding.registered_student_invite.app_entry_completed`

### Eventos por jornada

#### A. `mass_box_invite`

Eventos:

1. `student_onboarding.mass_box_invite.link_created`
2. `student_onboarding.mass_box_invite.landing_viewed`
3. `student_onboarding.mass_box_invite.oauth_started`
4. `student_onboarding.mass_box_invite.oauth_completed`
5. `student_onboarding.mass_box_invite.wizard_started`
6. `student_onboarding.mass_box_invite.wizard_completed`
7. `student_onboarding.mass_box_invite.app_entry_completed`

#### B. `imported_lead_invite`

Eventos:

1. `student_onboarding.imported_lead_invite.invite_created`
2. `student_onboarding.imported_lead_invite.whatsapp_handoff_opened`
3. `student_onboarding.imported_lead_invite.landing_viewed`
4. `student_onboarding.imported_lead_invite.oauth_started`
5. `student_onboarding.imported_lead_invite.oauth_completed`
6. `student_onboarding.imported_lead_invite.wizard_started`
7. `student_onboarding.imported_lead_invite.wizard_completed`
8. `student_onboarding.imported_lead_invite.app_entry_completed`

#### C. `registered_student_invite`

Eventos:

1. `student_onboarding.registered_student_invite.invite_created`
2. `student_onboarding.registered_student_invite.landing_viewed`
3. `student_onboarding.registered_student_invite.oauth_started`
4. `student_onboarding.registered_student_invite.oauth_completed`
5. `student_onboarding.registered_student_invite.app_entry_completed`

## 6. Funil oficial por jornada

### `mass_box_invite`

Etapas do funil:

1. `landing_viewed`
2. `oauth_started`
3. `oauth_completed`
4. `wizard_started`
5. `wizard_completed`
6. `app_entry_completed`

Leitura principal:

1. `visitantes`
2. `autenticacoes concluidas`
3. `cadastros concluidos`
4. `entradas no app`
5. `taxa de conclusao final`

### `imported_lead_invite`

Etapas do funil:

1. `invite_created`
2. `whatsapp_handoff_opened`
3. `landing_viewed`
4. `oauth_completed`
5. `wizard_completed`
6. `app_entry_completed`

Leitura principal:

1. `convites disparados`
2. `handoffs abertos`
3. `aceites reais`
4. `cadastros finalizados`
5. `ativacao final`

### `registered_student_invite`

Etapas do funil:

1. `invite_created`
2. `landing_viewed`
3. `oauth_completed`
4. `app_entry_completed`

Leitura principal:

1. `convites emitidos`
2. `acessos iniciados`
3. `logins concluidos`
4. `taxa de entrada direta`

## 7. Onde cada evento dispara

### `student_identity/staff_views.py`

Disparar:

1. `invite_created` para `imported_lead_invite`
2. `invite_created` para `registered_student_invite`
3. `link_created` para `mass_box_invite`
4. `whatsapp_handoff_opened` quando houver handoff do convite individual

Motivo:

1. esta e a porta oficial de operacao do convite

### `student_identity/views.py`

Disparar:

1. `landing_viewed` nas landings de convite
2. `oauth_started` ao iniciar o provedor
3. `oauth_completed` ao concluir callback com sucesso

Motivo:

1. esta e a borda oficial do invite + OAuth

### `student_app/views.py`

Disparar:

1. `wizard_started` ao abrir onboarding pendente
2. `wizard_completed` ao salvar onboarding com sucesso
3. `app_entry_completed` ao concluir entrada no app

Motivo:

1. aqui a jornada fecha de fato do ponto de vista do aluno

### `onboarding/views.py`

Disparar:

1. `whatsapp_handoff_opened` no fluxo `Convidar 1 clique`

Motivo:

1. esta e a origem canonica do corredor de lead importado

## 8. Payload minimo de cada evento

Campos minimos:

1. `journey`
2. `box_root_slug`
3. `invitation_id` ou `box_invite_link_id`
4. `student_id` quando existir
5. `identity_id` quando existir
6. `actor_id` quando a origem for operacao staff
7. `source_surface`
8. `occurred_at`

### `source_surface` oficial

Valores iniciais:

1. `student_invitation_operations`
2. `student_invite_landing`
3. `student_oauth_start`
4. `student_oauth_callback`
5. `student_onboarding_wizard`
6. `intake_center`
7. `student_app_home`

## 9. Como isso aparece no painel

### Princípio de UX

Adaptando a lente do payments UX para onboarding:

1. nao mostrar um cemitério de numeros
2. mostrar progresso, atrito e proxima acao
3. destacar o ponto de abandono mais caro

### Painel recomendado no card do `link em massa`

Bloco 1:

1. `Visitas no link`
2. `OAuth concluido`
3. `Cadastro concluido`
4. `Entrada no app`

Bloco 2:

1. `Taxa visita -> cadastro`
2. `Taxa OAuth -> cadastro`
3. `Abandonos em wizard`

Bloco 3:

1. alerta se `visitou muito e concluiu pouco`
2. alerta se `OAuth sobe e wizard nao fecha`

### Painel recomendado para convite individual

Colunas ou pills:

1. `Convidado`
2. `Abriu`
3. `Autenticou`
4. `Concluiu`

### Ordem visual recomendada

1. primeiro progresso
2. depois taxa
3. depois excecao

Regra de UX:

1. o olho precisa encontrar a conversao antes da tabela
2. a proxima acao precisa vir junto da metrica

## 10. Shape do `page payload`

### `student_identity/presentation.py`

Adicionar bloco como:

```python
"funnel": {
    "mass_box_invite": {
        "steps": [...],
        "summary_cards": [...],
        "alerts": [...],
    },
    "imported_lead_invite": {
        "steps": [...],
        "summary_cards": [...],
        "alerts": [...],
    },
    "registered_student_invite": {
        "steps": [...],
        "summary_cards": [...],
        "alerts": [...],
    },
}
```

### Motivo

1. manter a leitura no presenter
2. manter o template fino
3. permitir futura extração para query/snapshot

## 11. Faseamento sem debito tecnico

### Fase 1 - Instrumentacao minima

Entregas:

1. publicar os eventos oficiais em `AuditEvent`
2. contar:
   - `landing_viewed`
   - `oauth_completed`
   - `wizard_completed`
   - `app_entry_completed`
3. adicionar cards simples no painel

Por que vence:

1. pequeno corte
2. baixo risco
3. alto valor operacional

### Fase 2 - Snapshot operacional

Entregas:

1. extrair leitura de funil para `student_identity/queries.py` ou snapshot dedicado
2. deixar `staff_views.py` mais fino
3. consolidar janelas de 7d, 14d e 30d

Por que vence:

1. evita que a view vire planilha
2. prepara crescimento de leitura

### Fase 3 - Telemetria de superficie

Entregas:

1. surface telemetry para interacoes de painel
2. leitura de cliques em CTA do painel
3. detalhe de abandono entre landing e OAuth

Por que ainda nao:

1. valor menor que a fase 1
2. pode esperar ate o painel provar utilidade

## 12. Riscos e guardrails

### Risco 1 - confundir clique com conversao

Guardrail:

1. nunca misturar `landing_viewed` com `wizard_completed`

### Risco 2 - poluir o dominio com analitico

Guardrail:

1. publicar fatos na borda
2. ler agregacao na camada de snapshot

### Risco 3 - painel bonito e inutil

Guardrail:

1. cada card precisa responder uma decisao

Exemplos:

1. `visitou muito, concluiu pouco` -> revisar copy ou friccao de wizard
2. `handoff aberto, landing baixa` -> revisar mensagem do WhatsApp
3. `OAuth conclui, app entry baixa` -> revisar callback ou persistencia

## 13. Decisoes ADR curtas

### ADR 1 - usar `AuditEvent` na fase 1

Decisao:

1. usar `AuditEvent` como trilha inicial do funil

Porque:

1. ja existe
2. reduz custo de entrada
3. combina com a fase atual do produto

Trade-off:

1. nao e a forma final para leitura pesada

### ADR 2 - funil separado por jornada

Decisao:

1. medir cada corredor separadamente

Porque:

1. as taxas esperadas sao diferentes
2. misturar tudo gera leitura enganosa

### ADR 3 - painel orientado por decisao

Decisao:

1. mostrar progresso + taxa + proxima acao

Porque:

1. numero sozinho nao move operacao

## 14. Formula curta

O desenho correto e este:

1. publicar fatos pequenos na borda certa
2. agregar por jornada
3. mostrar progresso antes de volume
4. transformar metrica em proxima acao

Em linguagem de crianca:

1. contar quem viu a porta
2. contar quem entrou no corredor
3. contar quem chegou na sala
4. e avisar onde o caminho ficou escorregadio
