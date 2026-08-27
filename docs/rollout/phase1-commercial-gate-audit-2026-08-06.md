<!--
ARQUIVO: auditoria do gate da Fase 1 relida sob a promessa comercial de vender ate 20 boxes.

TIPO DE DOCUMENTO:
- auditoria de prontidao operacional

AUTORIDADE:
- alta para "podemos vender o box numero 2 ate o 20"
- nao substitui [first-box-production-execution-checklist.md](first-box-production-execution-checklist.md),
  que continua sendo o checklist do dia de go-live de cada box

DOCUMENTOS IRMAOS:
- [restore-and-rollback-drill.md](restore-and-rollback-drill.md)
- [hostgator/backup.md](hostgator/backup.md)
- [hostgator/restore.md](hostgator/restore.md)
- [../plans/phase1-closed-beta-20-boxes-corda.md](../plans/phase1-closed-beta-20-boxes-corda.md)
- [../plans/scale-transition-20-100-open-multitenancy-plan.md](../plans/scale-transition-20-100-open-multitenancy-plan.md)

QUANDO USAR:
- antes de abrir a venda dos boxes 2 a 20
- quando a duvida for "o que ainda impede a gente de prometer recuperacao para um cliente pagante"

POR QUE ELE EXISTE:
- o C.O.R.D.A. da Fase 1 e o checklist do primeiro box foram escritos ANTES da virada
  schema-per-tenant (2026-05). A evidencia de restore/rollback que fechou aqueles gates
  foi coletada num runtime de banco unico que nao existe mais.
- vender 20 boxes cria uma promessa que o trilho atual de recuperacao ainda nao cumpre:
  recuperar UM box sem mexer nos outros.

O QUE ESTE ARQUIVO FAZ:
1. separa o que esta provado, o que esta defasado e o que bloqueia a venda em escala.
2. nomeia o unico bloqueador real encontrado e o menor passo que o fecha.
3. define o gate objetivo para liberar a venda dos boxes 2 a 20.

PONTOS CRITICOS:
- este documento nao invalida o go-live atual: o box em producao esta coberto.
- o risco descrito aqui nasce a partir do SEGUNDO box pagante, nao do primeiro.
-->

# Auditoria do gate da Fase 1 sob a promessa comercial — 2026-08-06

## Pergunta que esta auditoria responde

Nao é "o primeiro box pode entrar?" — ele já entrou, em 2026-05-23, e está de pé.

A pergunta é: **podemos assumir com um cliente pagante a promessa de que, se der problema no box dele, a gente recupera o box dele?**

Hoje a resposta honesta é: *quase*. Falta uma peça, e ela é específica.

---

## 1. O que está provado (verde)

| Item | Evidência |
|---|---|
| Backup automatizado em produção | systemd `octobox-backup.timer` + cópia externa Cloudflare R2 via rclone, retenção 30 dias, alerta de idade máxima 36h e de disco em 85% — ver [hostgator/backup.md](hostgator/backup.md) |
| Restore PostgreSQL real executado | dump `octobox-20260414-013716.dump` restaurado em `octobox_restore_test`, app validada contra o banco restaurado (`/api/v1/health/` e `/operacao/owner/` = 200) — ver [archive/phase1-execution-evidence-2026-04-13.md](archive/phase1-execution-evidence-2026-04-13.md) |
| Rollback de aplicação ensaiado | worktree limpo, `dc5ef8a` → `9e0e2bb` → volta, com as 7 rotas centrais em 200 nas três rodadas |
| Rollback de aplicação em produção | `scripts/linux/rollback_octobox.sh` existe no trilho de deploy |
| Runtime boundary | `BOX_RUNTIME_SLUG`, `runtime_namespace` e `/api/v1/health/` validados |
| Resiliência das superfícies quentes | `intent_id` e `snapshot_version` ativos em `owner`, `manager` e `reception`, com fallback por versão |
| Ferramentas de ciclo de vida do tenant | `provision_box`, `reprovision_box`, `archive_box` e `smoke_test_tenant` existem e são anteriores à necessidade |
| Segurança mínima | admin em caminho privado, throttles por escopo, segredos fora do repo, HTTPS |

Leitura: a fundação está bem acima da média para o estágio. O trabalho invisível foi feito.

---

## 2. O que está defasado (amarelo) — evidência válida, runtime diferente

Esta é a parte que o índice de status não pega, porque nada quebrou: **a evidência envelheceu junto com a arquitetura.**

Toda a prova de restore da Fase 1 foi coletada em **2026-04-13/14**. Naquele momento o runtime era **banco único, schema único** — o log de execução mostra `migrate` (não `migrate_schemas`), 3 usuários de teste e validação por contagem em `auth_user`/`auth_group`.

Em **2026-05** o runtime virou schema-per-tenant com `django-tenants`, e em **2026-05-23** o primeiro box foi provisionado em `box_<slug>`.

Consequência concreta: **nunca foi provado um restore num cluster que tem schemas de tenant dentro.** Especificamente, continuam sem evidência:

1. que o dump full captura corretamente os schemas `box_*` (tecnicamente captura — schemas vivem no mesmo banco — mas *provado* é diferente de *presumido*);
2. que o isolamento entre tenants sobrevive ao restore;
3. que `smoke_test_tenant --slug <box>` passa contra um banco restaurado;
4. que `control_box`/`control_domain` (schema `public`) voltam consistentes com os schemas de tenant restaurados — se o control plane e os schemas divergirem, o box existe no banco mas o roteamento não acha.

Item adicional de higiene: a tabela de registro em [restore-and-rollback-drill.md](restore-and-rollback-drill.md) está com **todas as linhas `pendente`**, apesar de o drill ter sido executado e arquivado. Quem ler o doc ativo conclui, erradamente, que nada foi provado. Isso foi corrigido na mesma rodada desta auditoria.

---

## 3. O bloqueador real (vermelho) — restore por tenant não existe

Este é o único achado que muda decisão comercial.

**O trilho de recuperação atual é all-or-nothing no cluster.** [hostgator/restore.md](hostgator/restore.md) descreve restaurar o banco inteiro num banco isolado e, no desastre, apontar a aplicação para ele. Não há — em script, runbook ou comando — o caminho de restaurar **um** box.

Por que isso não doeu até agora: com 1 box, "restaurar o cluster" e "restaurar o box" são a mesma operação.

Por que passa a doer a partir do box 2:

| Cenário real e banal | O que acontece hoje |
|---|---|
| Dono importa CSV errado e duplica 200 alunos | Para voltar o box dele ao estado de ontem, **todos os outros boxes voltam junto** — perdendo o dia de trabalho deles |
| Recepção executa ação em massa indevida no financeiro | Mesma coisa |
| Box pede offboarding e depois quer os dados de volta | `archive_box` existe, mas não há caminho provado de trazer só aquele schema de volta |

Ou seja: a promessa comercial "eu recupero o seu box" hoje só é verdadeira se **nenhum outro box tiver trabalhado desde o backup**. Isso deixa de ser verdade no dia em que existir o segundo cliente pagante.

Agravante de negócio: é exatamente essa a promessa que sustenta a garantia de 60 dias e o discurso de "seus dados são seus" na oferta de fundador. Vender isso sem o trilho é vender o que não se tem.

**Menor passo que fecha:** dump e restore por schema. `pg_dump -n box_<slug>` e `pg_restore` seletivo já resolvem — o que faltava era ferramenta, runbook e um ensaio.

Entregue nesta rodada:

1. [`scripts/linux/backup_tenant_schema.sh`](../../scripts/linux/backup_tenant_schema.sh) — dump de um box só.
2. [`scripts/linux/restore_tenant_schema.sh`](../../scripts/linux/restore_tenant_schema.sh) — restore não destrutivo em banco isolado.
3. Parte C do [restore-and-rollback-drill.md](restore-and-rollback-drill.md) — o ensaio, incluindo a sequência de **promoção** para o banco vivo (manual e explícita, com `ALTER SCHEMA ... RENAME` como rede de segurança).

> **Estado dos scripts:** escritos, revisados, **não ensaiados**. O aceite deles é a Parte C do drill, e ela exige um cluster PostgreSQL com pelo menos 2 tenants — não existe nesta máquina (`pg_dump`, `pg_restore` e `psql` ausentes; só `docker` disponível). O drill é a próxima ação, não a leitura desta auditoria.

---

## 4. O que NÃO é bloqueador (e não deve virar escopo agora)

Registrado para impedir que a auditoria vire obra:

1. **Backup por tenant automatizado e agendado** — o dump full diário já protege o dado; o dump por tenant é ferramenta de recuperação cirúrgica, e sob demanda basta para 20 boxes. Automatizar por box é assunto de Fase 2.
2. **Point-in-time recovery (WAL archiving)** — resolveria o problema com mais elegância, mas é infraestrutura de Fase 2/3. Para 20 boxes, dump diário + restore cirúrgico é proporcional.
3. **Observabilidade por box** — está no gate da Fase 2, não no da 1.
4. **Custo por box medido** — o gate de saída da Fase 1 pede isso, mas ele bloqueia a *passagem para a Fase 2*, não a venda dos boxes 2 a 20.

---

## 5. Gate objetivo para liberar a venda dos boxes 2 a 20

Liberar quando as cinco linhas forem verdadeiras:

1. [ ] Drill Parte C executado: dump de um tenant, restore isolado, `smoke_test_tenant` verde no banco restaurado.
2. [ ] Sequência de promoção ensaiada ao menos uma vez em homologação, incluindo o `ALTER SCHEMA ... RENAME` de segurança e o retorno.
3. [ ] Tempo medido da recuperação de um box (do "achei o dump" ao "smoke verde") — é o número que define o SLA que se pode prometer em venda.
4. [ ] Registro do drill preenchido com evidência real na tabela do drill (data, arquivo, horários, responsável).
5. [ ] Uma linha no material comercial dizendo o que a garantia cobre de verdade, com o tempo medido no item 3.

Enquanto o item 1 não fechar: **pode vender, mas não pode prometer recuperação individual** — e é melhor não vender do que prometer o que não se ensaiou.

---

## Fórmula curta

A Fase 1 provou que a casa sobe, sabe quem é e sabe voltar.

O que ela ainda não provou é voltar **um cômodo** sem mexer no resto da casa. Com um morador isso é filosofia. Com vinte, é o contrato.
