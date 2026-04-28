<!--
ARQUIVO: indice de navegacao da pasta docs/map.

TIPO DE DOCUMENTO:
- guia de entrada
- indice de mapas tecnicos

AUTORIDADE:
- media para navegacao dentro de `docs/map`
- baixa para substituir `docs/reference/reading-guide.md` ou docs canonicos

DOCUMENTO PAI:
- [../reference/reading-guide.md](../reference/reading-guide.md)

DOCUMENTOS IRMAOS:
- [../reference/documentation-authority-map.md](../reference/documentation-authority-map.md)
- [../guides/README.md](../guides/README.md)

QUANDO USAR:
- quando a pergunta for "qual mapa eu abro primeiro?"
- quando `docs/map` parecer uma pasta boa, mas espalhada
- quando um agente ou dev precisar localizar um corredor sem abrir 20 arquivos

POR QUE ELE EXISTE:
- a pasta `docs/map` cresceu e ja tem mapas fortes em varias frentes
- sem indice, a pessoa sabe que existe material bom, mas ainda perde tempo escolhendo a porta
- este arquivo organiza a pasta por pergunta, nao apenas por ordem alfabetica

O QUE ESTE ARQUIVO FAZ:
1. separa mapas por corredor e por intencao.
2. cria atalhos curtos por pergunta comum.
3. destaca os mapas mais vivos e os mapas mais historicos.
4. reduz busca cega em `docs/map`.

PONTOS CRITICOS:
- este indice nao substitui o runtime real.
- se um mapa ficar obsoleto, ele deve ser corrigido ou reclassificado aqui.
- se um tema importante crescer, vale ganhar sua propria secao.
-->

# Indice de mapas tecnicos

Esta pasta e como uma sala de mapas do predio.

Os guias em `docs/guides/` sao a recepcao.
O `docs/reference/reading-guide.md` e o corredor principal de leitura tecnica.
Ja `docs/map/` guarda mapas mais focados, cirurgicos e operacionais.

Traducao simples:

1. o guia diz por onde entrar no predio
2. o reading guide mostra os andares
3. esta pasta mostra a planta detalhada de alguns corredores especificos

## Como usar esta pasta

Se voce ainda nao sabe quase nada sobre o projeto, comece por:

1. [../../README.md](../../README.md)
2. [../guides/README.md](../guides/README.md)
3. [../reference/documentation-authority-map.md](../reference/documentation-authority-map.md)
4. [../reference/reading-guide.md](../reference/reading-guide.md)

Depois disso, use `docs/map` quando a pergunta ficar mais especifica.

## Atalho por pergunta

Se a pergunta for "como o app do aluno funciona?", abra:

1. [student-app-complete-map.md](./student-app-complete-map.md)
2. [student-app-path-map.md](./student-app-path-map.md)

Se a pergunta for "como a pagina WOD do aluno e montada?", abra:

1. [student-app-wod-page-structure-map.md](./student-app-wod-page-structure-map.md)
2. [student-app-wod-communication-map.md](./student-app-wod-communication-map.md)

Se a pergunta for "como o WOD operacional conversa com o app do aluno?", abra:

1. [student-app-wod-communication-map.md](./student-app-wod-communication-map.md)
2. [../reference/operations-wod-ownership-map.md](../reference/operations-wod-ownership-map.md)

Se a pergunta for "como o frontend esta organizado ou quem e dono do que?", abra:

1. [front-end-ownership-map.md](./front-end-ownership-map.md)
2. [front-end-runtime-boundary-map.md](./front-end-runtime-boundary-map.md)
3. [front-end-forensics-map.md](./front-end-forensics-map.md)
4. [front-end-data-action-contract-map.md](./front-end-data-action-contract-map.md)

Se a pergunta for "qual e o circuito de debug do frontend?", abra:

1. [front-end-forensics-checklist.md](./front-end-forensics-checklist.md)
2. [front-end-error-patterns-map.md](./front-end-error-patterns-map.md)
3. [front-end-data-action-debug-checklist.md](./front-end-data-action-debug-checklist.md)

Se a pergunta for "como cache e busca no frontend se conectam?", abra:

1. [front-end-search-cache-contract-map.md](./front-end-search-cache-contract-map.md)
2. [cache-readiness-map.md](./cache-readiness-map.md)

Se a pergunta for "como o comercial/leads entra no sistema?", abra:

1. [leads-intake-cadastro-alunos-map.md](./leads-intake-cadastro-alunos-map.md)

Se a pergunta for "qual mapa ajuda a pensar por testes?", abra:

1. [1-map-by-tests.md](./1-map-by-tests.md)

## Mapas por corredor

### 1. App do aluno

Use quando o foco for `/aluno/`, identidade do aluno, shell mobile/PWA, grade, WOD, RM e configuracoes.

Arquivos:

1. [student-app-complete-map.md](./student-app-complete-map.md)
2. [student-app-path-map.md](./student-app-path-map.md)
3. [student-app-wod-page-structure-map.md](./student-app-wod-page-structure-map.md)
4. [student-app-wod-communication-map.md](./student-app-wod-communication-map.md)

Leitura recomendada:

1. `complete`
2. `path`
3. `wod page`
4. `wod communication`

### 2. Frontend e contratos visuais

Use quando o foco for ownership de tela, limites entre layout/dados/acao, forensics, dark mode, visual smoke ou risco de override.

Arquivos:

1. [front-end-ownership-map.md](./front-end-ownership-map.md)
2. [front-end-runtime-boundary-map.md](./front-end-runtime-boundary-map.md)
3. [front-end-data-action-contract-map.md](./front-end-data-action-contract-map.md)
4. [front-end-dashboard-action-contract-map.md](./front-end-dashboard-action-contract-map.md)
5. [front-end-forensics-map.md](./front-end-forensics-map.md)
6. [front-end-contract-forensics-map.md](./front-end-contract-forensics-map.md)
7. [front-end-error-patterns-map.md](./front-end-error-patterns-map.md)
8. [front-end-neon-contract-map.md](./front-end-neon-contract-map.md)
9. [design-system-contract.md](./design-system-contract.md)

### 3. Frontend checklists e auditoria

Use quando o foco for depuracao guiada, smoke manual, debug por contrato ou revisao visual.

Arquivos:

1. [front-end-forensics-checklist.md](./front-end-forensics-checklist.md)
2. [front-end-contract-only-visual-smoke-checklist.md](./front-end-contract-only-visual-smoke-checklist.md)
3. [front-end-contract-only-visual-smoke-report-template.md](./front-end-contract-only-visual-smoke-report-template.md)
4. [front-end-data-action-debug-checklist.md](./front-end-data-action-debug-checklist.md)

### 4. Frontend por ondas e auditorias de frente

Use quando o foco for mapas de fase, auditorias pontuais ou material de reestruturacao do frontend.

Arquivos:

1. [front-end-wave1-catalog-shared-audit.md](./front-end-wave1-catalog-shared-audit.md)
2. [front-end-wave4-contract-audit.md](./front-end-wave4-contract-audit.md)
3. [front-end-wave4-operations-dependency-map.md](./front-end-wave4-operations-dependency-map.md)
4. [front-end-owner-workspace-audit.md](./front-end-owner-workspace-audit.md)
5. [dashboard-darkmode-cascade-roadmap.md](./dashboard-darkmode-cascade-roadmap.md)
6. [finance-darkmode-wave1-map.md](./finance-darkmode-wave1-map.md)

### 5. Finance e snapshots

Use quando a pergunta for sobre checkpoint estrutural de financeiro, snapshot canonico ou leitura de estado.

Arquivos:

1. [finance-architecture-checkpoint.md](./finance-architecture-checkpoint.md)
2. [finance-snapshot-canonical-map.md](./finance-snapshot-canonical-map.md)

### 6. Cache, esqueleto e mapas mais estruturais

Use quando o foco for readiness, esqueleto de leitura ou mapas mais amplos de estrutura.

Arquivos:

1. [cache-readiness-map.md](./cache-readiness-map.md)
2. [1skeleton-roadmap.md](./1skeleton-roadmap.md)
3. [documentation-authority-map.md](./documentation-authority-map.md)

## Mapas mais vivos hoje

Se eu tivesse que abrir poucos arquivos primeiro nesta pasta, eu priorizaria:

1. [student-app-complete-map.md](./student-app-complete-map.md)
2. [student-app-wod-communication-map.md](./student-app-wod-communication-map.md)
3. [front-end-ownership-map.md](./front-end-ownership-map.md)
4. [front-end-runtime-boundary-map.md](./front-end-runtime-boundary-map.md)
5. [front-end-forensics-map.md](./front-end-forensics-map.md)
6. [leads-intake-cadastro-alunos-map.md](./leads-intake-cadastro-alunos-map.md)

## Regra simples de manutencao

Quando um mapa novo nascer, tente responder primeiro:

1. ele e de app do aluno, frontend, finance, leads ou estrutura?
2. ele e mapa de ownership, de debug, de checklist ou de auditoria?
3. qual pergunta concreta ele responde?
4. qual arquivo desta pasta deve apontar para ele?

Se essas respostas nao estiverem claras, o risco e criar mais um mapa bom perdido dentro da gaveta.

