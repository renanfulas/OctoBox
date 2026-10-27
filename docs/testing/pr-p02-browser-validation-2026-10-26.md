# Validação do PR P02 — WOD Mobile Gates — 2026-10-26

Branch `codex/wod-mobile-gates`, empilhada sobre o P01 (`codex/wod-drafts-and-confirmation`). A matriz declarada pelo workflow executa quatro arquivos em Chromium e WebKit, usa PostgreSQL 15 descartável e deixa artefatos JUnit/traces quando há falha. Os JUnit locais foram gerados em `tmp/p02-chromium.xml` e `tmp/p02-webkit.xml` e não entram no commit.

## Resultado local

- YAML do workflow: parseado com sucesso.
- Chromium: **73 passed** em 245,15 s.
- WebKit: **73 passed** em 521,21 s.
- Check sintático e migrations da aplicação: herdados do P01; não há mudanças de modelo neste pacote.

Uma falha inicial mostrou que o login de Owner sincroniza sessões passadas para concluídas. O teste de distribuição customizada agora autentica antes de criar as aulas, e o teste do calendário também faz login antes de acessar a tela protegida. Os casos focais e a matriz completa passaram após essa correção.

Ambas as matrizes emitiram somente o warning de diretório `staticfiles` ausente no checkout local.

## Limites

O teste iPhone usa viewport/device em browser de desktop. Isso não substitui Safari em iPhone físico, teclado virtual, instalação PWA nem validação de push. Branch protection não foi alterada; o workflow precisa ser marcado como required check separadamente.
