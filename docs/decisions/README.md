<!--
ARQUIVO: log de decisões e lições — a memória durável do "porquê" do projeto.

POR QUE ELE EXISTE:
- o índice do RAG é descartável (vive no Postgres, regenera com ingest). O que precisa
  sobreviver é o APRENDIZADO. Este diretório é esse ativo versionado.
- cada lição vira um arquivo curto, indexado pelo RAG com autoridade média-alta (82),
  para reaparecer quando alguém perguntar sobre a mesma área no futuro.

QUANDO ESCREVER (o gate — não escreva por escrever):
- só quando o PR/mudança teve um aprendizado NÃO-ÓBVIO e reutilizável:
  gotcha, causa-raiz não trivial, achado de performance, contrato que quebrou,
  ou decisão arquitetural. Se foi mecânico/óbvio, NÃO crie lição (evita poluir o índice).

COMO ESCREVER:
- use a skill `/pr-lesson` (destila do diff + resultado do check) ou siga o template abaixo.
- numere sequencial: `NNNN-slug-curto.md`. Cite sempre `arquivo:linha`.

ENVELHECIMENTO:
- lição é fotografia de um momento. Se o runtime divergir, o runtime vence e a lição
  perde autoridade (ver docs/reference/documentation-authority-map.md). Marque como
  `status: superseded by NNNN` quando uma lição nova substituir a antiga.
-->

# Decisions & Lessons log

Memória durável do "porquê". O RAG indexa esta pasta com autoridade **82** para que cada
lição reapareça na busca sobre a mesma área. Escreva só o que for **não-óbvio e reutilizável**.

## Template

```markdown
<!-- ARQUIVO: lição NNNN — <título>. -->
# NNNN — <título curto>

- **date:** YYYY-MM-DD
- **area:** `arquivo:linha`, `arquivo:linha` (os arquivos no centro da mudança)
- **status:** active | superseded by NNNN

## O que mudou
<1-3 linhas: a mudança em si.>

## Por quê
<a causa/contexto que tornou a mudança necessária.>

## Lição / padrão reutilizável
<1-3 linhas: o aprendizado que se aplica a futuros casos parecidos. Esta é a parte que importa.>
```

## Índice

- [0001 — `knowledge` (RAG) movido para SHARED + gotcha de migração django-tenants](0001-knowledge-shared-migration.md)
- [0002 — Deploy saiu do Render para HostGator VPS](0002-render-to-hostgator-vps.md)
