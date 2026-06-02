<!-- ARQUIVO: lição 0001 — knowledge (RAG) movido de TENANT_APPS para SHARED_APPS. -->
# 0001 — `knowledge` (RAG) movido para SHARED + gotcha de migração django-tenants

- **date:** 2026-05-30
- **area:** `config/settings/base.py` (SHARED_APPS/TENANT_APPS), `knowledge/schema_access.py`, `knowledge/management/commands/search_project_knowledge.py`, `knowledge/management/commands/ingest_project_knowledge.py`
- **status:** active

## O que mudou
O app `knowledge` (RAG interno) saiu de `TENANT_APPS` para `SHARED_APPS`: agora é **um índice único no schema `public`**, indexado uma vez — não mais uma cópia por box. A CLI (`search_project_knowledge`/`ingest_project_knowledge`) voltou a funcionar "bare", sem `--box`/`tenant_command`.

## Por quê
O índice do RAG é conteúdo do **repositório** (idêntico para todo tenant), então duplicá-lo por box (~13.7k chunks vezes N) era desperdício e quebrava a CLI no `public` com `relation "knowledge_knowledgechunk" does not exist`.

## Lição / padrão reutilizável
1. **Conteúdo de repositório (não dado de tenant) pertence a `SHARED_APPS`**, no `public`. Use o teste mental: "isso é igual em todo box? → shared".
2. **Gotcha django-tenants ao mover TENANT→SHARED num banco existente:** as migrations podem estar **pré-gravadas** em `public.django_migrations` sem as tabelas (o `TenantSyncRouter` registra a migration como aplicada mas pula o DDL no schema errado). Sintoma: `migrate_schemas --shared` diz "nothing to do" mas a tabela não existe. **Fix:** `migrate_schemas --shared <app> zero --fake` → `migrate_schemas --shared <app>` para criar de verdade; depois `DROP` das tabelas órfãs nos schemas `box_*`. Clones novos não sofrem disso.
3. Em SQLite o `migrate` nem roda (`'DatabaseWrapper' object has no attribute 'set_schema'`): django-tenants exige PostgreSQL.
