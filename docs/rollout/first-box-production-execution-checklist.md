<!--
ARQUIVO: checklist executavel de producao para colocar o primeiro box no ar.

TIPO DE DOCUMENTO:
- checklist operacional de execucao

AUTORIDADE:
- alta para a Fase 1 do beta fechado

DOCUMENTOS IRMAOS:
- [homologation-deploy-checklist.md](homologation-deploy-checklist.md)
- [first-box-system-setup-checklist.md](first-box-system-setup-checklist.md)
- [first-box-onboarding-runbook.md](first-box-onboarding-runbook.md)
- [beta-internal-release-gate.md](beta-internal-release-gate.md)
- [phase1-closed-beta-operations-matrix.md](phase1-closed-beta-operations-matrix.md)
- [restore-and-rollback-drill.md](restore-and-rollback-drill.md)
- [postgres-homolog-provisioning-checklist.md](postgres-homolog-provisioning-checklist.md)
- [../plans/scale-transition-20-100-open-multitenancy-plan.md](../plans/scale-transition-20-100-open-multitenancy-plan.md)

QUANDO USAR:
- antes de colocar o primeiro box em operacao real
- no dia do go-live do primeiro box
- como gate de pronta-entrega da Fase 1 ate 20 boxes

POR QUE ELE EXISTE:
- junta infraestrutura, liberacao e operacao do primeiro box em uma ordem unica.
- evita o erro classico de "deploy pronto, mas operacao nao pronta" ou "usuario pronto, mas runtime torto".
- transforma a Fase 1 em passos verificaveis, nao em confianca abstrata.

O QUE ESTE ARQUIVO FAZ:
1. define a sequencia exata de verificacao antes do primeiro box.
2. separa bloqueador de detalhe.
3. amarra healthcheck, runtime boundary, seguranca, setup interno e smoke operacional.

PONTOS CRITICOS:
- este checklist e para o primeiro box do beta fechado, nao para rollout em massa.
- se um item bloqueador falhar, o box nao entra.
- nao usar este documento para ampliar escopo no dia da implantacao.
-->

# Checklist executavel de producao do primeiro box

## Objetivo

Colocar o primeiro box em producao real com o menor risco possivel, mantendo a Fase 1 fiel ao plano:

1. ate 20 boxes
2. 1 servidor
3. isolamento forte
4. beta fechado

Em linguagem simples:

1. primeiro garantir que a casa tem endereco, energia, agua e chave
2. depois colocar os moveis
3. so entao deixar a familia entrar

## Definicao de pronto

O primeiro box so pode entrar em uso real quando estas quatro frases forem verdadeiras ao mesmo tempo:

1. o ambiente sobe e responde
2. o runtime sabe qual box/celula representa
3. os usuarios do box conseguem operar o pacote minimo
4. existe backup, rollback e suporte para o primeiro susto

---

## Etapa 0. Congelar o escopo do primeiro box

Antes de qualquer deploy ou cadastro, confirmar que o primeiro box vai entrar apenas com o pacote curto da Fase 1:

1. login e papeis
2. dashboard
3. alunos
4. cadastro e edicao leve
5. grade em leitura
6. Recepcao
7. cobranca curta
8. manager e owner no fluxo minimo oficial

Bloqueador:

1. tentar vender integracao pesada, customizacao grande ou operacao fora do pacote no dia do go-live

Referencia:

1. [first-box-rollout-plan.md](first-box-rollout-plan.md)
2. [first-box-onboarding-runbook.md](first-box-onboarding-runbook.md)

---

## Etapa 1. Validar homologacao e infraestrutura

Executar a base tecnica antes de encostar no box.

Checklist:

1. deploy publicado com `DJANGO_ENV=production`
2. `DATABASE_URL` real configurada
3. `REDIS_URL` real configurada
4. `DJANGO_ALLOWED_HOSTS` configurado
5. `DJANGO_CSRF_TRUSTED_ORIGINS` configurado
6. `bootstrap_roles` executado
7. superuser criado
8. `OPERATIONS_MANAGER_WORKSPACE_ENABLED=True` no ambiente do piloto quando o papel Manager fizer parte do pacote do dia 1
9. `/api/v1/health/` responde `status=ok`
10. `/login/`, `/dashboard/`, `/operacao/`, `/alunos/` e `/grade-aulas/` respondem sem 500
11. assets carregam com CSS e JS corretos

Bloqueador:

1. qualquer rota central com 500
2. healthcheck falhando
3. manager exigido no piloto mas workspace desabilitado por flag
4. assets quebrados
5. login falhando

Referencia:

1. [homologation-deploy-checklist.md](homologation-deploy-checklist.md)
2. [postgres-homolog-provisioning-checklist.md](postgres-homolog-provisioning-checklist.md)

---

## Etapa 2. Validar a fronteira do runtime do box

Aqui confirmamos se a "caixa" do box esta etiquetada corretamente no runtime.

Checklist:

1. `BOX_RUNTIME_SLUG` definido no ambiente
2. `BOX_RUNTIME_SLUG` nomeia claramente o box piloto ou a celula atual
3. `CACHE_KEY_PREFIX` mantido no baseline oficial
4. `/api/v1/health/` responde `runtime_slug` coerente
5. `/api/v1/health/` responde `runtime_namespace` coerente
6. o runtime atual nao usa prefixo generico confuso compartilhado por acidente

Formula pratica:

1. `runtime_slug` = nome da casa
2. `runtime_namespace` = etiqueta do quadro de luz

Bloqueador:

1. runtime sem slug
2. namespace generico que nao identifica a celula atual

---

## Etapa 3. Validar seguranca minima de producao

Checklist:

1. `DJANGO_SECRET_KEY` fora do repositorio
2. admin protegido por `DJANGO_ADMIN_URL_PATH` nao obvio
3. throttles ativos com baseline da Fase 1
4. `SECURITY_TRUSTED_PROXY_IPS` configurado quando houver proxy real
5. `SECURITY_BLOCKED_IPS` e `SECURITY_BLOCKED_IP_RANGES` vazios ou preenchidos por evidencia real
6. HTTPS ativo
7. cookies e redirect HTTPS coerentes para o ambiente

Bloqueador:

1. admin exposto no caminho padrao
2. segredo no repo
3. producao sem HTTPS
4. throttle desligado ou sem baseline conhecida

Referencia:

1. [../reference/production-security-baseline.md](../reference/production-security-baseline.md)
2. [../reference/external-security-edge-playbook.md](../reference/external-security-edge-playbook.md)

---

## Etapa 4. Validar resiliencia da Fase 1

Checklist:

1. `intent_id` ativo nos fluxos criticos do manager e cobranca por WhatsApp
2. `snapshot_version` emitido em `owner`, `manager` e `reception`
3. `manager` refresca por versao sem repaint inutil
4. `reception` refresca por versao quando SSE falhar ou estiver ausente
5. `owner` refresca por versao com polling leve
6. o sistema nao parece morto quando o barramento quente falha

Bloqueador:

1. workspace quente congelado sem fallback
2. clique operacional sem reconciliacao visual minima

Referencia:

1. [../plans/unit-cascade-architecture-plan.md](../plans/unit-cascade-architecture-plan.md)
2. [../plans/scale-transition-20-100-open-multitenancy-plan.md](../plans/scale-transition-20-100-open-multitenancy-plan.md)

---

## Etapa 5. Validar backup e rollback

Checklist:

1. backup inicial do banco gerado
2. arquivo de backup com timestamp confirmado
3. local do backup documentado
4. homologacao PostgreSQL provisionada com banco principal, banco isolado de restore, Redis e envs criticas
5. restore testado ao menos uma vez em ambiente isolado ou homolog
6. rollback de aplicacao descrito
7. responsavel pelo rollback definido

Bloqueador:

1. backup inexistente
2. homologacao PostgreSQL ainda nao provisionada para o drill real
3. restore nunca testado
4. rollback dependendo de improviso

Referencia:

1. [backup-guide.md](backup-guide.md)
2. [restore-and-rollback-drill.md](restore-and-rollback-drill.md)
3. [postgres-homolog-restore-runbook.md](postgres-homolog-restore-runbook.md)
4. [postgres-homolog-provisioning-checklist.md](postgres-homolog-provisioning-checklist.md)

---

## Etapa 6. Preparar os dados e usuarios do box

Checklist:

1. ficha do box preenchida em [first-box-pilot-intake-sheet.md](first-box-pilot-intake-sheet.md)
2. usuarios reais criados por papel
3. login de pelo menos um usuario por papel testado
4. planos minimos cadastrados
5. base inicial de alunos pronta para importacao ou cadastro manual
6. grade essencial da semana definida

Bloqueador:

1. usuario sem papel claro
2. box sem owner operacional
3. grade essencial indefinida

Referencia:

1. [first-box-system-setup-checklist.md](first-box-system-setup-checklist.md)

---

## Etapa 7. Executar setup interno do primeiro box

Executar a ordem interna sem inventar atalhos:

1. validar acesso base
2. criar usuarios
3. cadastrar planos
4. carregar base inicial de alunos
5. montar grade essencial
6. testar Recepcao
7. testar cobranca curta
8. smoke test por papel

Gate:

1. se falhar um item critico, corrigir antes de seguir

Referencia:

1. [first-box-system-setup-checklist.md](first-box-system-setup-checklist.md)

---

## Etapa 8. Smoke funcional do go-live

Validar manualmente, nesta ordem:

1. login
2. dashboard
3. owner em `/operacao/owner/`
4. manager em `/operacao/manager/`
5. reception em `/operacao/recepcao/`
6. alunos em `/alunos/`
7. grade em `/grade-aulas/`
8. health em `/api/v1/health/`

Confirmar em cada area:

1. contexto correto
2. contadores coerentes
3. CTA principal aponta para fluxo real
4. sem permissao indevida entre papeis

Bloqueador:

1. CTA morto
2. contador obviamente incoerente
3. papel com acesso indevido

Referencia:

1. [beta-internal-release-gate.md](beta-internal-release-gate.md)

---

## Etapa 9. Teste operacional do dia 1

Rodar pelo menos um circuito real de ponta a ponta:

1. localizar aluno
2. editar aluno
3. abrir Recepcao
4. ver grade
5. tratar uma cobranca curta
6. abrir um contato operacional quando o caso exigir

Objetivo:

1. provar que o produto nao esta apenas bonito; ele precisa respirar numa rotina real

Bloqueador:

1. fluxo central so funciona via admin bruto
2. operador nao consegue completar o ciclo curto sem pedir socorro a cada clique

---

## Etapa 10. Registrar o go-live

Ao fim da implantacao, registrar:

1. nome do box
2. `BOX_RUNTIME_SLUG`
3. URL do ambiente
4. data e hora do go-live
5. usuarios criados
6. quantidade de alunos importados
7. quantidade de planos cadastrados
8. responsavel tecnico
9. responsavel operacional
10. pendencias abertas

---

## Etapa 11. Definir o war room dos primeiros 7 a 14 dias

Checklist:

1. canal unico para suporte do piloto
2. responsavel por triagem tecnica definido
3. janela de resposta combinada
4. criterio de severidade combinado
5. rotina diaria curta de revisao nos primeiros dias

Bloqueador:

1. box entrar sem saber para onde mandar bug
2. time tecnico sem dono claro do suporte inicial

Referencia:

1. [pilot-support-playbook.md](pilot-support-playbook.md)
2. [operations-realtime-war-room-playbook.md](operations-realtime-war-room-playbook.md)

---

## Gate final de liberacao

Liberar o primeiro box so quando todos estes itens estiverem verdes:

1. homologacao publicada e saudavel
2. runtime boundary correta
3. seguranca minima aplicada
4. resiliencia da Fase 1 validada
5. backup e restore validados
6. setup interno concluido
7. smoke funcional concluido
8. circuito real do dia 1 concluido
9. war room inicial definido

Se qualquer um falhar:

1. o box nao entra
2. corrigir
3. repetir apenas o bloco necessario e voltar ao gate

## Formula curta

Para o primeiro box entrar sem susto, precisamos poder dizer:

1. a casa sobe
2. a casa sabe quem ela e
3. a equipe consegue trabalhar nela
4. se der problema, a gente sabe voltar e socorrer
