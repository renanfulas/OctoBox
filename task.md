<!--
ARQUIVO: quadro curto de execucao e auditoria da fase atual.

POR QUE ELE EXISTE:
- Mantem a fotografia honesta do fechamento de beta sem depender de memoria oral.
- Registra o que foi validado, o que esta em progresso e o que ainda precisa de confirmacao externa.

O QUE ESTE ARQUIVO FAZ:
1. resume o estado das ondas do fechamento de beta.
2. marca os ajustes tecnicos auditados na Onda 3.1.
3. aponta os proximos passos que ainda dependem de verificacao manual.

PONTOS CRITICOS:
- este arquivo nao substitui o board oficial do front nem o runtime real.
- sempre que o status mudar no codigo, este quadro precisa mudar junto.
-->

# Task: Fechamento de Beta (C.O.R.D.A.)

## Referencias de autoridade

- [README.md](README.md)
- [docs/plans/front-beta-closure-board.md](docs/plans/front-beta-closure-board.md)
- [docs/experience/mobile-real-validation-round-1-2026-03-29.md](docs/experience/mobile-real-validation-round-1-2026-03-29.md)
- [docs/experience/mobile-real-validation-round-2-2026-03-28-assisted.md](docs/experience/mobile-real-validation-round-2-2026-03-28-assisted.md)
- [docs/experience/mobile-real-validation-round-3-2026-03-28-students-postfix.md](docs/experience/mobile-real-validation-round-3-2026-03-28-students-postfix.md)
- [docs/experience/mobile-real-validation-round-4-2026-03-29-browser-assisted-postfix.md](docs/experience/mobile-real-validation-round-4-2026-03-29-browser-assisted-postfix.md)
- [docs/experience/mobile-real-validation-round-5-2026-03-29-iphone13-browser-assisted.md](docs/experience/mobile-real-validation-round-5-2026-03-29-iphone13-browser-assisted.md)
- [.specs/codebase/CONVENTIONS.md](.specs/codebase/CONVENTIONS.md)

## Onda 1. Auditoria tecnica

- [x] Registrar metodologia C.O.R.D.A. em `.specs/codebase/CONVENTIONS.md`
- [x] Executar auditoria tecnica de shell, login, recepcao e alunos
- [x] Registrar reporte mobile em `docs/experience/mobile-real-validation-round-1-2026-03-29.md`

## Onda 2. Correcao de bloqueadores

- [x] Corrigir grid da recepcao para empilhamento mobile
- [x] Implementar responsive grid para KPIs de alunos
- [x] Melhorar o sidebar toggle para o fluxo mobile
- [x] Remover CSS inline do template de login

## Onda 3.1. Saneamento estrutural

- [x] Mover o CSS do login para `static/css/design-system/pages/login.css`
- [x] Remover o artefato espelho em `staticfiles/css/design-system/pages/login.css`
- [x] Adicionar carga automatica de `.env` em entrypoints locais
- [x] Fazer `python manage.py test` preferir `config.settings.test`
- [x] Tornar a leitura de `SECRET_KEY` mais resiliente para ambiente local e CI
- [x] Expor governanca OctoBox e C.O.R.D.A. no `README.md`

## Onda 3.2. Fechamento tecnico e validacao assistida

- [x] Alinhar o contrato de throttle da recepcao com `test_reception_payment_action_blocks_burst_requests`
- [x] Reabrir dashboard e sidebar para coach e recepcao, mantendo o contrato dos testes
- [x] Deixar `boxcore.tests.test_operations` totalmente verde
- [x] Rodar validacao browser-assisted multi-viewport em `320px`, `390px` e `430px` com browser externo real
- [x] Registrar a rodada em `docs/experience/mobile-real-validation-round-2-2026-03-28-assisted.md`
- [x] Atualizar o board beta com o resultado da rodada assistida

## Proximos passos ainda abertos

- [x] Corrigir a faixa de acoes e filtros do diretorio de alunos em `320px` para remover o overflow lateral de ~43px
- [x] Revalidar o diretorio de alunos em `320px`, `390px` e `430px` apos o patch responsivo
- [x] Atacar o pan lateral do shell como polimento pre-piloto
- [x] Revalidar `login`, `dashboard`, `recepcao` e `alunos` em `320px`, `390px` e `430px` apos os patches finais
- [x] Executar passada browser-assisted no perfil de `iPhone 13`
- [x] Executar confirmacao fisica com toque real para shell, busca, recepcao, alunos e ficha leve
- [x] Revalidar autocomplete da busca global com dataset local que devolva resultados reais
- [x] Smoke test humano rotas centrais (Beta Gate)
- [x] Smoke test humano perfis Owner, Recepcao, Coach, Gerente
- [x] Sincronizar painel `front-beta-closure-board.md` apos checklist manual
- [x] Validar e remover ghost/ghost (usuario de dev blindado contra ambiente de homologacao real)

## Pos-gate. Hub de relatorios gerenciais V1

- [x] Centralizar a estrategia de exportacao no Hub Gerencial em `/operacao/relatorios/`
- [x] Remover a exportacao direta da tela de `Alunos` para manter a superficie operacional enxuta
- [x] Remover os botoes visuais de exportacao CSV/PDF do fluxo principal enquanto a reforma de UI/UX estiver em andamento
- [x] Limpar payloads e variaveis de export do fluxo de `Alunos`
- [x] Corrigir o `Book Comercial` para voltar a responder sem erro `500`
- [x] Alinhar o `Book Comercial` com colunas gerenciais basicas: nome, contato, status, plano, financeiro e ultimo check-in
- [ ] Auditar e remediar a qualidade do campo `WhatsApp` no `Book Comercial`

## Observacoes operacionais do V1

- A exportacao de alunos nao faz mais parte da tela operacional `Alunos`; a fonte canonica de export passa a ser o Hub de Relatorios.
- Durante a reforma da experiencia principal, os comandos visuais de CSV/PDF ficam fora da interface e voltam apenas no fechamento operacional.
- No ambiente local atual, os valores de `WhatsApp` estao armazenados como ciphertext `gAAAAA...` e nao estao sendo decifrados pelo runtime, indicando legado cifrado com chave divergente ou irrecuperavel.
- Enquanto a remediacao de dados nao for concluida, o `Book Comercial` esta funcional como pipeline, mas o campo `WhatsApp` nao pode ser tratado como dado gerencial confiavel.
