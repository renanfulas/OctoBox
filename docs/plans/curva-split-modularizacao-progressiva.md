# Curva — plano de split progressivo

Estado do mapeamento: 13/10/2026. Este documento descreve o checkout atual; não afirma implantação ou homologação em PWA instalada.

**Execução local em 13/10/2026:** cortes A, B, C, D e E aplicados, mais o primeiro grupo do F. `load-api.js` contém transporte; `assessments-report.js` renderiza o relatório; `guided-state.js` projeta o treino; `load-sync.js` e `guided-sync.js` coordenam filas sem DOM. O 409 de duas correções de carga offline preserva a segunda para revisão, exportação, reaplicação ou descarte explícito. Catálogo, acesso e entrega PWA estão em módulos próprios, com reexports temporários na view. Template e precache foram atualizados; epoch do PWA passou de 10 para 11. Código local não equivale a deploy nem a homologação em PWA instalada.

## 1. Regra de decisão

Dividir por responsabilidade e contrato, não por quantidade de linhas. Cada corte deve deixar um dono claro para estado, dados e efeitos; manter as URLs, o HTML entregue, os códigos HTTP e as chaves locais; e ser revisável sozinho. Um arquivo menor que apenas redistribui referências globais não melhora a arquitetura.

Fontes de navegação: [plano técnico do guia](curva-treino-guiado-plano-tecnico-rag.md), [mapa da montagem do treino](../coaching/guia-montagem-treino-curva.md), [runbook de analytics](../runbooks/curva-funnel-analytics.md) e o código citado abaixo. O RAG local apontou esses documentos; as prioridades abaixo foram conferidas contra os módulos e consumidores atuais.

## 2. O que ainda é relativamente fácil

| Corte | Situação observada | Valor e decisão |
|---|---|---|
| `load-api.js` | Antes do corte, `load_tracker.js` continha `getCookie`, `postJson` e `fetchLastLoadByMovement`, além de formulário e fila. | **Feito.** Transporte isolado com `{ok,status,data}` e erro de rede como rejeição; sincronização continua no controlador. |
| Visualização de avaliações | Antes do corte, `assessments.js` tinha cerca de 860 linhas e misturava silhueta, cartões, medidas, linha do tempo, gráfico, formulário e POST. | **Feito.** `assessments-report.js` recebe o relatório e devolve HTML sem DOM/rede/armazenamento; formulário e montagem continuam em `assessments.js`. |
| Glossário do shell | `workout-shell.js` contém posicionamento e alternância das dicas, além de navegação de abas/ciclo. | **Adiar.** O ganho é menor que o custo de outro asset e nova ordem de carregamento. Só extrair quando houver evolução própria do glossário. |
| Mais includes de 20–40 linhas, CSS de perfil isolado ou um utilitário HTTP global | O template e o CSS já têm cortes por área; `assessments.js` e `load_tracker.js` têm carregamentos diferentes em páginas legadas e unificadas. | **Evitar agora.** Fragmentação adicional aumentaria o mapa de dependências sem remover estado misturado. Não fundir APIs só porque ambas usam `fetch`. |

Cada JS novo entra no template correspondente **e** no allowlist do service worker em `student_app/views/public_workout_views.py`; a ordem de `defer` deve respeitar dependências. A versão do cache usa a lista de assets e mtime, mas `PUBLIC_WORKOUT_CACHE_EPOCH` exige avaliação explícita quando HTML ou semântica de cache mudar. `assessments.js` também carrega em páginas legadas: qualquer extração sua precisa atualizar os dois caminhos.

## 3. Mapa do emaranhado que resta

| Núcleo atual | Responsabilidades acopladas | Fronteira desejada | Risco dominante |
|---|---|---|---|
| `static/js/public_workouts/load_tracker.js` (~887 linhas) | Outbox, rascunho, correção, formulário, feedback, substituição e compartilhamento. | `load-api.js` já saiu; próximo é coordenador de envio/fila; `load-storage.js` e calculadora continuam donos atuais. | O `drainOutbox` descarta 409, inclusive possível segunda correção offline; não perpetuar perda silenciosa ao mover código. |
| `static/js/public_workouts/workout-guided.js` (~709 linhas) | Plano lido do DOM, sessão, conjuntos realizados/pulados, fila/lease, conflitos e renderização. | `guided-state.js` já projeta o passo e a conclusão; próximos são controlador DOM e coordenador de comandos. | Duas fontes de verdade, mudança indevida na ordem de replay, lease entre abas e conclusão prematura. |
| `student_app/views/public_workout_views.py` (1804 linhas) | Catálogo estático, versão de assets, posse/assinatura, renderização legada/unificada, PWA e endpoints de negócio. | Catálogo independente → política de acesso → renderização/PWA → endpoints por recurso, com fachada de imports. | Ciclo com `public_workouts.services`, vazamento entre alunos, consultas a TENANT_APPS no schema `public`, 404 que vira 403. |
| `public_workouts/services.py` (1396 linhas) | Avaliação, programa/draft, perfis, nutrição, pacote, carga e exportação. | Serviços de domínio por caso de uso com `services.py` como fachada temporária. | Muitos consumidores importam a fachada; testes de isolamento analisam seu AST e precisam passar a cobrir módulos extraídos. |
| `public_workouts/models.py` (1469 linhas) | Vários domínios de modelos Django na mesma aplicação. | Só dividir em pacote de modelos por domínio quando houver mudança real nesses modelos. | Registro de modelos, migrações históricas, imports e nome de classe serializado. Um split cosmético aqui tem custo alto. |

Dependência circular concreta hoje: `public_workouts/services.py::_validate_plan_slug` importa `PUBLIC_WORKOUT_LIBRARY` de `student_app.views.public_workout_views` dentro da função; a view importa funções de `services.py` tardiamente. `public_workout_sessions.py`, `public_workout_push.py` e `public_workout_assessment_views.py` importam helpers da view grande. Portanto o split Python começa pelo catálogo puro, não pelas classes HTTP.

## 4. Sequência executável, do simples ao difícil

### Corte A — transporte da carga (baixo risco)

1. Criar `static/js/public_workouts/load-api.js` com `postLoad(slug, entry)` e `lastTopSetByMovement(slug)`. Preservar credenciais, CSRF, headers, interpretação do corpo e formato de retorno atuais. Não mover política de retry ou feedback para esse módulo.
2. Substituir chamadas de `postJson`/`fetchLastLoadByMovement` em `load_tracker.js`. O controlador continua decidindo 400/401/409, fila e mensagens. Atualizar template, allowlist e caminho de páginas que realmente carregam o tracker.
3. Provar equivalência: envio online, rascunho, reconexão, 401 com texto preservado e dica de última Top. Verificar a ordem dos scripts e a resposta do service worker.

### Corte B — renderização das avaliações (baixo a médio risco)

1. Extrair do bloco visual de `assessments.js` as constantes SVG, helpers de escape/formatação e builders de cartões, silhueta, medidas, linha do tempo e gráfico para `assessments-report.js`. Definir API pequena, por exemplo `CurvaAssessmentReport.render(report)`, sem capturar `form`, `panel`, `fetch` ou `localStorage`.
2. Deixar `assessments.js` com montagem, formulário, validação, POST, GET e atualização do slot. O formulário deve sobreviver ao refresh do relatório como hoje.
3. Incluir o novo script nas páginas legadas e no template unificado e no precache. Conferir relatório vazio, duas avaliações, valores escapados e desbloqueio das dobras cutâneas vindo do servidor.

### Corte C — estado puro do treino guiado (médio a alto risco)

1. Registrar contratos de entrada/saída da projeção atual em `paintStep`: `movements`, `recorded`, `skipped`, `pending`, `lastSkipped`, `lastFreeformIndex` → próximo passo, total, contagem, séries obrigatórias restantes e opções de concluir/corrigir/adicionar. Criar `guided-state.js` sem DOM, rede, relógio ou IndexedDB. A função recebe cópias ou dados imutáveis e não altera os argumentos.
2. Substituir em `workout-guided.js` só os cálculos de `paintStep`, mantendo nele texto, campos, foco e timer. Não mudar simultaneamente a política de carga, etapas opcionais ou o protocolo de comandos.
3. Reusar a mesma projeção em `workout-offline.js` apenas depois de provar que o plano salvo no dispositivo tem o mesmo formato; evitar duplicar a máquina de estado ou reescrever o fluxo offline durante a primeira extração.
4. Cobrir Top/Feeder, séries opcionais, série livre, pular/desfazer, corrigir e concluir com pendências. Confirmar que “feito no aparelho” e “confirmado pelo servidor” continuam estados distintos.

### Corte D — sincronização da carga e comandos do guia (alto risco, em dois diffs)

1. **Carga:** mover `drainOutbox`, política de retry e reconciliação para `load-sync.js`, com portas explícitas (`api`, `storage`, `onConfirmed`, `onBlocked`). O módulo não conhece seletores nem escreve HTML. Antes de finalizá-lo, decidir e implementar o tratamento de 409 offline: manter a entrada bloqueada e exportável/reabrível como rascunho, sem descartá-la silenciosamente. Isso é correção funcional separada da extração mecânica, com teste próprio.
2. **Guia:** mover `deliver`, `drain`, lease, remapeamento de `local_session_id`, 401/409 e ordem de comandos para `guided-sync.js`, preservando `guided-outbox.js` como persistência e `guided-api.js` como transporte. Expor eventos/resultados para o controlador atualizar UI e snapshot. Um único coordenador deve possuir `pending`, `blockedCommand`, `draining` e lease; o controlador não replica esses campos.
3. Casos obrigatórios: duas abas, aba encerrada após POST antes do recibo, sessão expirada, rede que cai entre início/série/fim, 409 corrigível, exportação, logout/troca de conta e sequência de duas correções offline. Replay deve continuar idempotente e em ordem.

### Corte E — catálogo e autorização Python (alto risco)

1. Criar módulo de catálogo sem imports de `services.py`: `PublicWorkoutAccent`, `PublicWorkoutPlan`, `PUBLIC_WORKOUT_LIBRARY` e constantes próprias. `services.py::_validate_plan_slug` passa a consultar esse módulo, fechando o ciclo de importação atual. Manter reexports antigos enquanto consumidores são migrados.
2. Criar `public_workout_access.py` para lookup/síntese do plano, cookie de posse, assinatura ativa e posse da conta. Preservar 404, distinção entre bloqueio visual do dono na página e 404 nos endpoints, e imports tardios dos modelos quando necessários. Atualizar primeiro as views de sessão/push/avaliação, depois a view grande.
3. Não confundir cookie B0 com identidade de login. Uma política de acesso pode oferecer operações diferentes para página, API e download; evitar um decorador genérico que altere esse comportamento.
4. Provar em schema `public` real ou teste de isolamento equivalente que nenhum import novo alcança modelo de TENANT_APPS. Verificar slug alheio, assinatura inativa, conta anônima, legado pago fora do Stripe e cookies inválidos.

### Corte F — views e serviços por recurso (alto risco)

1. Mover PWA/manifest/offline e gestão de assets para módulo de entrega; renderização de página/preview para outro; pacote, revisão, dieta, exportação, carga e avaliação para módulos HTTP por recurso. Manter `student_app.views` e, temporariamente, `public_workout_views.py` como fachadas para URLs e imports existentes. Migrar um grupo de endpoints por vez.
2. Em `public_workouts/services.py`, separar primeiro avaliação e nutrição, depois programa/draft, pacote e carga. Preservar assinaturas públicas em fachada durante a transição. Mover ou ampliar os testes AST de isolamento hoje fixados em `services.py`, para inspecionar todos os módulos do corredor.
3. Só então avaliar `models.py`. Se a equipe continuar adicionando modelos, criar pacote `public_workouts/models/` com imports explícitos em `__init__.py`, mantendo `app_label`, nomes e import paths compatíveis com migrações históricas. Fazer como mudança exclusiva e verificar `makemigrations --check --dry-run`; não usar o tamanho atual como justificativa suficiente.

## 5. Hierarquia de verificação por corte

1. **Contrato local:** JS syntax e testes de função pura para estado/renderização; testes Python de import, assinatura e permissões para catálogo/acesso. A extração mecânica deve ser comparada com comportamento anterior antes de qualquer correção funcional.
2. **Integração:** endpoint e banco para carga/sessão; renderização e asset allowlist; isolamento em schema `public`; `manage.py check` e `makemigrations --check --dry-run` nos cortes Python.
3. **Jornada no navegador:** treino guiado online/offline/409/401, registro de carga e avaliação em página unificada e legada. Reusar E2E existentes e adicionar apenas o caso que o corte ainda não cobre.
4. **PWA instalada:** após mudanças de asset/cache e no portão de ativação ampla, conferir abertura offline, atualização do service worker e interação no iPhone e Android reais. Teste local de navegador não substitui essa homologação.

Critério de aceitação comum: sem mudança de rota pública, contratos JSON, códigos de erro, chaves de armazenamento, dados de sessão, escopo por conta, ordem de scripts e aparência em temas/mobile. Quando um corte falhar, reverter apenas sua integração (import/asset/fachada), preservando dados já gravados.

## 6. Estado e próximos cortes

`A ✓ → B ✓ → C ✓ → D(carga) ✓ → D(guia) ✓ → E(catálogo/acesso) ✓ → F(PWA) ✓ → F(restante)`. `workout-guided.js` continua dono da tela e da projeção visual; `guided-sync.js` é o único dono de `pending`, conflito, replay e lease. `public_workouts/catalog.py` é independente de ORM/views; `student_app/views/public_workout_access.py` resolve catálogo ativo, assinatura, posse e cookie. `student_app/views/public_workout_pwa.py` possui assets, versão, manifest, service worker e fallback offline. `services.py` já consulta o catálogo sem importar a view. O restante do F migra endpoints um grupo por vez; `models.py` fica por último e só entra se o crescimento justificar o custo.

Não misturar split com nova interface ou regra de treino, salvo a perda de correção offline 409 explicitada em D; nesse caso, entregar a correção em diff e teste próprios antes de mudar o coordenador. O trabalho operacional de push e a homologação do treino continuam descritos no [plano técnico](curva-treino-guiado-plano-tecnico-rag.md) e não são substituídos por esta refatoração.

### Resultado do corte D e preparação do F

`load-sync.js` usa o banco existente e mantém entradas bloqueadas com motivo e registro ativo recebido do servidor. A tela apresenta os valores locais e do servidor; oferece cópia JSON, reaplicação com nova chave e descarte confirmado. O servidor percorre a cadeia de correções da conta para apontar o registro ativo. `guided-sync.js` centraliza fila, lease, replay e conflito, preservando `guided-outbox.js` como persistência e `guided-api.js` como transporte.

O primeiro grupo HTTP do F já saiu: PWA/manifest/offline, com reexports na view grande. O próximo grupo recomendado é leitura do pacote/revisão/nutrição, mantendo fachada para URLs/imports existentes. Antes de mover cada classe, listar consumidores, preservar 404/cookie/assinatura e conferir o teste de schema `public`. Não mover `services.py` inteiro nem `models.py` numa operação só.

**Verificação desta rodada:** 17 testes Node, 49 testes Django focados de catálogo, acesso, PWA, carga, push e sessão, e 11 E2E de guia, calculadora, avaliação e revisão visual do 409 passaram. `manage.py check`, `makemigrations --check --dry-run`, sintaxe JS e `git diff --check` passaram. Um teste antigo em `public_workouts/test_program.py::PublishProgramTests::test_known_movement_is_not_touched` falha isoladamente porque tenta criar `agachamento-livre` já presente no banco de teste; o teste precisa ser reconciliado com o seed antes de usá-lo como gate. Homologação em iPhone/Android PWA instalada segue pendente.
