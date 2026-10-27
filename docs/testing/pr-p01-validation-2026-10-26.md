# Validação do PR P01 — 2026-10-26

Branch `codex/wod-drafts-and-confirmation`, extraída sobre `origin/main` em `096edb0b055f2f2e20d6aed0caa42ff9e634c090`. A árvore de origem local continua sem alterações de índice; os resultados antigos do checkout combinado não são usados como prova desta branch.

## Ambiente

- PostgreSQL 15 descartável em container local, porta `127.0.0.1:55436`, banco `octobox_pr`.
- Django usa `config.settings.test`, migrations ativadas.
- Nenhuma chamada a provider externo; dados dos testes são sintéticos.

## Resultado

- `manage.py check`: sem problemas.
- `manage.py makemigrations --check --dry-run`: nenhuma migration adicional detectada.
- `git diff --check`: limpo após remover os trechos de testes que pertencem ao pacote P11.
- Suíte de domínio: **300 passed, 25 subtests passed** em 281,42 s.
- Gate Chromium/WebKit pertence ao P02 e permanece pendente.

## Fronteira dos pacotes

A primeira execução integrada obteve 295 aprovações e 5 falhas. Quatro testes verificavam redação de conteúdo sensível em auditoria (aprovação/rejeição, follow-up e governança semanal); um verificava sanitização de exceção no parser semanal. Os produtores e a sanitização global pertencem aos pacotes P11. Esses quatro trechos de teste foram removidos de P01 e registrados como pendências de propriedade no manifesto de extração. Os fluxos WOD do pacote permanecem cobertos por suas suítes específicas. A repetição passou integralmente. Pytest avisou que não conseguiu encerrar o banco `test_octobox_pr` porque duas conexões continuavam ativas; isso ocorreu após os testes concluírem, sem falhas de caso. O warning de diretório `staticfiles` ausente também veio do ambiente de checkout isolado.

## Limites

Os testes exercitam ACL, drafts, CAS de versão, fingerprint, replay, locks PostgreSQL, modalidades compartilhando `ClassType`, parser e projeção. A matriz de browser deve ser validada em P02. Provider real, piloto com Coach e iPhone físico requerem ambientes externos e não são alegados como verificados.
