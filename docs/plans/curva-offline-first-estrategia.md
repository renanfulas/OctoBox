# Curva offline-first — diagnóstico e estratégia

> **Escopo:** o app do aluno da Curva (PWA em `/renan/<slug>`). O painel do
> treinador (`/treinos/coach`) fica fora desta estratégia — ele pressupõe
> conexão e roda no contexto autenticado do box.
>
> **Objetivo pedido:** o app precisa funcionar sem internet (academias em
> subsolo/galpão fechado), com **o mesmo comportamento do online**, e ao
> voltar a conexão tudo que foi registrado localmente sobe para o servidor
> sozinho, sem duplicar.

---

## 1. Diagnóstico — por que hoje o app NÃO funciona offline

O PWA existe e tem service worker, mas o offline atual é **de fallback
degradado por decisão de segurança**, não por falta de infraestrutura.

### 1.1 O HTML do treino nunca entra em cache (causa principal)

Em `templates/public_workouts/sw.js`, o handler de navegação é
network-first **sem cache da página**: offline, qualquer navegação para
`/renan/<slug>` cai em `/renan/offline/` (página genérica de fallback).

Isso foi deliberado: a versão antiga do SW pré-cacheava as páginas de
**todos** os alunos, e o aparelho da Juliana guardava o %gordura do Bruno
(achado A4 do CORDA, `docs/plans/public-workouts-produtizacao-corda.md`).
A correção removeu o cache de página **inteiro** em vez de cachear só a
página do dono — trocou o vazamento por "offline não abre o app".

### 1.2 Todo dado dinâmico é network-only (B0)

O SW ignora de propósito qualquer URL sob `/renan/` que termine em
`.json`, `/sessao` ou `/push` — dado de saúde nunca entra no Cache Storage
compartilhado do navegador (decisão B0 do CORDA). Correto para privacidade,
mas sem uma camada local substituta, offline = sem dados.

### 1.3 O gate de acesso exige servidor

O acesso é provado por cookie assinado de posse (`renan_slug`, ver
`student_app/views/public_workout_access.py`). Offline não há quem valide
o cookie nem quem renderize a página — o modelo atual é 100%
server-rendered por requisição.

### 1.4 O que existe offline hoje é um "modo de emergência"

`/renan/offline/` + `static/js/public_workouts/workout-offline.js` montam
um registrador mínimo que só funciona se:
- o aluno abriu o treino guiado online antes (escopo salvo em
  `localStorage` `curva-guided-scope:<slug>`);
- a ficha snapshot no IndexedDB tem **menos de 7 dias**;
- não há encerramento pendente na fila.

E mesmo quando funciona: sem abas (nutrição, avaliações, progresso), sem o
visual do app, sem histórico de cargas — longe de "mesmo comportamento que
online".

### 1.5 Fragilidades de atualização que pioram o quadro

- `PUBLIC_WORKOUT_CACHE_EPOCH` é bump **manual** (já vai em 23); esquecer o
  bump deixa instalações antigas servindo asset velho para sempre.
- `STATIC_ASSET_VERSION` fica congelada em `'1'` em produção (era do
  Render; a VPS não seta) — o fallback por mtime segura as pontas, mas é
  implícito.

### 1.6 Cobertura desigual das escritas

| Escrita | Offline hoje |
|---|---|
| Sessão guiada (séries, pulos, encerramento) | ✅ outbox IndexedDB (`guided-outbox.js` + `guided-sync.js`) |
| Carga confirmada | ✅ outbox com `idempotency_key` (`load-storage.js` + `load-sync.js`) |
| Avaliações (`/avaliacoes`) | ❌ POST direto, falha offline — ✅ fila + idempotência desde a F2 |
| Revisão semanal | ❌ leitura só online (é GET, não escrita) — ✅ cópia local desde a F2 |
| Onboarding | ❌ POST direto — ✅ fila desde a F2 |

---

## 2. O que já existe e a estratégia REAPROVEITA

A base offline de escrita é sólida e testada — não se reescreve, se
generaliza:

- **`guided-outbox.js`** — IndexedDB particionado por conta
  (`curva-guided:<scope>`): fila de comandos com sequência, write-ahead,
  lease multi-aba, mapeamento `local_session_id → session_id` do servidor,
  snapshot da ficha protegido por `program_version`.
- **`guided-sync.js`** — drenagem ordenada com retry, comandos bloqueados
  (conflito) com UI de resolução, tratamento de 401 (fila sobrevive),
  refresh GET pós-drenagem.
- **`load-storage.js` / `load-sync.js`** — outbox de cargas com
  `idempotency_key` (servidor já é idempotente em `record_load`) e
  rascunhos locais.
- **SW com precache completo de assets** — todo CSS/JS do template único já
  abre offline; o que falta é a página e os dados.

---

## 3. Estratégia — app-shell sem dado pessoal + dados por conta no IndexedDB

### Princípio central

> **Cache Storage (compartilhado) só guarda o que é igual para todos os
> alunos. Dado pessoal vive exclusivamente no IndexedDB particionado por
> conta.** Isso preserva A4 e B0 e ainda assim entrega offline completo.

O IndexedDB por escopo de conta já é o padrão aceito no projeto (outbox
guiado e de cargas); a estratégia estende esse padrão às **leituras**.

### 3.1 Pilar 1 — App shell cacheável (o HTML vira neutro)

Separar `workout.html` em **casca sem dado pessoal** + **hidratação por
dados**:

1. Criar rota `/renan/app-shell` que renderiza o template único **sem
   nenhum dado de aluno** (mesmos `<link>`/`<script>` de hoje, corpo com
   containers vazios). Mesmos bytes para qualquer aluno ⇒ pode entrar no
   precache do SW sem ferir A4.
2. No SW, navegação para `/renan/<slug>` offline responde com a casca do
   cache (em vez do fallback atual). Online continua network-first (a
   página server-rendered atual segue valendo — migração gradual, ver
   fases).
3. A casca, ao abrir: valida o marcador local de posse
   (`curva-guided-scope:<slug>` vinculado à conta autenticada); slug sem
   marcador ⇒ tela "abra com internet uma vez" (equivalente ao 404 do
   gate). Nunca hidrata dado de outro escopo.

### 3.2 Pilar 2 — Read model local (snapshot por conta)

Toda leitura passa a ter um repositório com dupla fonte:

1. Em **cada visita online**, a página persiste no IndexedDB do escopo um
   **snapshot de hidratação completo**: o equivalente a `pacote.json` +
   `nutricao.json` + `avaliacoes.json` + histórico de cargas, carimbado com
   `program_version` e `saved_at`. (Hoje só a ficha do guiado é salva, e
   apenas quando o guiado roda — `saveOfflinePlan` em `workout-guided.js`;
   passa a salvar sempre, para todas as abas.)
2. Offline, a casca renderiza **tudo** a partir do snapshot — mesmas abas,
   mesmo visual, mesmos componentes.
3. Online, padrão stale-while-revalidate **na camada do app** (nunca no
   Cache Storage): pinta do IndexedDB, busca da rede, atualiza tela e
   snapshot. B0 permanece intacto — `.json` continua fora do SW.
4. TTL do snapshot: subir dos 7 dias atuais para **30 dias** (academia com
   internet ruim fica semanas sem sincronizar), com aviso visual de "dados
   de X dias atrás".

### 3.3 Pilar 3 — Outbox universal (todas as escritas)

Generalizar o padrão guiado/cargas para **todas** as mutações:

- Avaliações, revisão semanal e onboarding passam pela mesma fila:
  `idempotency_key` UUID gerada no cliente, ordenação por sequência,
  comando bloqueado em conflito com UI de resolução (já existe no guiado).
- Servidor: todo endpoint de escrita ganha idempotência (coluna
  `idempotency_key` + unique constraint, como `record_load`) e aceita
  carimbo de tempo do cliente (`performed_at`) — registro feito offline às
  19h não pode entrar como "do dia seguinte" quando sincronizar às 8h.
- Regra de ouro já provada no projeto: **write-ahead** — primeiro grava na
  fila local, depois tenta a rede. A série nunca se perde por aba fechada.

### 3.4 Pilar 4 — Sincronização ao voltar a conexão

Gatilhos de drenagem (todos já têm metade do caminho em `guided-sync.js`):

1. Evento `online` da janela e abertura/retorno de foco da página.
2. **Background Sync API** no SW (`sync` event) como melhoria progressiva —
   Android/Chrome drena mesmo com o app fechado; iOS não suporta, então o
   fallback é a drenagem na abertura (comportamento atual).
3. Retry com backoff enquanto houver fila (já existe: 5s).
4. Lease multi-aba impede envio duplo (já existe).
5. **UI de estado de sync** persistente: badge "N registros aguardando
   envio" + idade do mais antigo, visível em todas as abas — o aluno e o
   treinador precisam confiar que nada se perdeu.

### 3.5 Pilar 5 — Autenticação e privacidade offline

- Offline não há como validar o cookie de posse ⇒ o gate local é o
  marcador de escopo gravado por sessão autenticada (padrão atual).
- 401 na drenagem: a fila **não** é descartada (já é assim); o app pede
  novo login e drena em seguida.
- `sair` (`/renan/<slug>/sair`) deve apagar IndexedDB + marcadores locais
  do escopo — verificar e cobrir com teste (aparelho compartilhado de
  recepção é cenário real de box).
- Invariantes mantidas: casca sem dado pessoal no Cache Storage (A4);
  `.json` jamais no Cache Storage (B0); dado pessoal só em IndexedDB por
  conta.

### 3.6 Pilar 6 — Versionamento e atualização

- Definir `STATIC_ASSET_VERSION` por deploy na VPS (hash do commit no env
  do serviço) — mata a dependência do bump manual para asset trocado;
  `PUBLIC_WORKOUT_CACHE_EPOCH` continua existindo só para expurgo forçado
  de segurança.
- Conflito de versão de programa: manter a proteção existente do
  `savePlan` (nunca sobrescreve ficha com sessão ativa de outra versão) e
  o fluxo de comando bloqueado para sessão antiga sincronizada tarde.
- `navigator.storage.persist()` na instalação do PWA — reduz risco de o
  iOS/Android expurgarem o IndexedDB com fila pendente.

---

## 4. Fases de entrega

| Fase | Entrega | Esforço | Valor |
|---|---|---|---|
| **F0 — ganho rápido** | Snapshot da ficha salvo em **toda** visita online (não só no guiado); TTL 7→30 dias; drenagem no evento `online`; badge de pendências; `storage.persist()` | dias | o modo de emergência atual passa a funcionar de forma confiável |
| **F1 — treino offline pleno** | Página do dono servida do IndexedDB pelo SW (ver §4.1 — substituiu a casca neutra); Background Sync adiado para F3 | 1–2 semanas | o fluxo principal (treinar na academia fechada) fica idêntico ao online |
| **F2 — paridade total** | Nutrição (leitura), avaliações e revisão semanal (outbox universal + idempotência no servidor), progresso/histórico local | 1–2 semanas | "mesmo comportamento que online" completo |
| **F3 — endurecimento** | UX de conflito unificada, telemetria de idade de fila, e2e Playwright offline por fluxo, auditoria de limpeza no `sair` (fila pendente + ficha, com aviso de perda), Background Sync no Android | contínuo | confiança operacional |

Cada fase exige bump do `PUBLIC_WORKOUT_CACHE_EPOCH` (HTML/precache mudam)
— já é o processo documentado em `public_workout_pwa.py`.

### 4.1 Status de implementação

**F0 — entregue (epoch 24).** Já existiam: snapshot da ficha em toda
visita online (`saveOfflinePlan` no init de `workout-guided.js`) e drenagem
no evento `online` (guiado e cargas). Adicionado: TTL 7→30 dias
(`workout-offline.js`), selo global de pendências (`sync-badge.js`, ouvindo
`curva:outbox-changed` emitido por `guided-outbox.js` / `load-storage.js`;
conta o guiado pela conexão viva via `CurvaGuidedOutbox.count`) e
`navigator.storage.persist()` (`workout-pwa.js`).

**F1 — entregue (epoch 25), com uma troca de técnica em relação ao §3.1.**
Em vez de uma casca neutra `/renan/app-shell` + re-renderização no cliente,
o service worker guarda **a própria página server-rendered do dono** no
IndexedDB (`curva-offline-pages`, chave = slug) e a serve sem rede:

- *Por quê:* o guiado e as cargas já funcionam 100% offline quando a página
  está aberta (início local com `local_session_id`, write-ahead, retomada do
  IndexedDB, drenagem no `online`/foco). O único bloqueio era a página não
  existir offline. Guardar a página real dá paridade imediata com o online e
  elimina o risco "casca e página divergirem" do §5 — não há segundo template.
- *Privacidade (A4/B0 preservados):* nada de página entra no Cache Storage;
  `.json` continua fora do SW. O servidor autoriza a cópia pelo header
  `X-Curva-Offline-Scope` (`PUBLIC_WORKOUT_OFFLINE_SCOPE_HEADER`), posto
  **só** na página real do dono logado (`PublicWorkoutDetailView`). Login
  expirado (redirect), 401/403/404 e resposta sem o header (pagamento
  bloqueado) apagam a cópia; 5xx não. `POST /renan/<slug>/sair` apaga a
  cópia no SW; "Apagar dados" do modo de emergência também. TTL 30 dias.
  Exposição = o tier já aceito no §5 (dado de saúde no aparelho, por conta).
- *Rede ruim:* com cópia salva, a navegação espera a rede no máximo 5 s
  (`PAGE_NETWORK_TIMEOUT_MS`); a resposta tardia só atualiza a cópia. 5xx
  com cópia salva também abre a cópia.
- *UX:* o SW marca `<body data-offline-snapshot="<ms>">`; `offline-banner.js`
  mostra "Modo offline · treino salvo em dd/mm às hh:mm" e, com a rede de
  volta, "Atualizar" (nunca recarrega sozinho — pode haver série em curso).
  Em página viva, a faixa aparece só enquanto o aparelho está sem conexão.
- *Background Sync (Android) — adiado para a F3.* A drenagem depende do
  contexto da página (ordem da fila, mapa `local_session_id → session_id`,
  UI de comando bloqueado) e o SW não lê o cookie CSRF; portá-la para o SW
  duplicaria `guided-sync.js`. iOS não tem a API de qualquer forma; a
  drenagem ao abrir/voltar o foco cobre o caso real.
- *Fora da F1:* abas de nutrição/avaliações dependem de `.json` e mostram o
  próprio erro offline (F2). A cópia mostra o estado da última visita online
  (ex.: dia concluído offline aparece pendente até a próxima visita online).
- *Provas:* `tests/js/curva_service_worker_offline_page.test.js`,
  `tests/js/curva_offline_banner.test.js`,
  `student_app/test_public_workout_ownership_gate.py::PublicWorkoutOfflineSnapshotConsentTests`
  e o e2e `test_app_opens_complete_without_network_and_syncs_when_it_returns`
  (navegador real: abre offline, treina pelo guiado, sincroniza ao voltar,
  e nenhuma página do aluno no Cache Storage).

**F2 — entregue (epoch 26).** Novo `offline-data.js`: um banco por conta
(`curva-offline-data:<conta>`) com dois stores.

- *Leituras (`reads`, chave = URL):* nutrição (`nutricao.json`), avaliações
  (`avaliacoes.json`), dicas de carga (`pacote.json`) e revisão semanal
  guardam a última resposta boa; sem rede ou com 5xx abrem a cópia (30 dias)
  com "Sem conexão: … salvo neste aparelho em dd/mm às hh:mm"; 401/403/404
  apagam a cópia daquela URL. Continua fora do Cache Storage (B0).
- *Escritas (`writes`, chave = `idempotency_key`):* autoavaliação e fim do
  onboarding passam pela fila write-ahead; 2xx e recusa 4xx saem da fila,
  401/5xx/sem rede ficam; drena ao abrir, no `online` e ao voltar o foco; o
  selo de pendências soma esta fila. Recusa de uma avaliação enviada depois
  aparece no formulário (`curva:offline-write-settled`).
- *Servidor:* `PublicWorkoutAssessment.idempotency_key` (unique, migration
  0051) — reenvio devolve a mesma linha; chave de outro aluno dá 409 e nunca
  devolve a avaliação dele. `measured_at` já é a data do aparelho.
- *Limpeza:* "Sair da conta" e as revogações do §4.1 limpam o store `reads`
  da conta no SW; o store `writes` fica (mesma regra da fila do guiado —
  apagar pendência com aviso é F3).
- *Limites:* a avaliação nova só entra no relatório depois do envio (o
  %gordura é calculado no servidor) — até lá o relatório mostra "N avaliações
  aguardando envio". O tutorial de onboarding pode reaparecer na cópia
  offline até a marca subir.
- *Revisão semanal:* só leitura (GET); não havia escrita a cobrir.
- *Provas:* `tests/js/curva_offline_data.test.js`, SW/selo estendidos,
  `PublicWorkoutRecordAssessmentIdempotencyTests` e o e2e
  `test_assessment_recorded_offline_reaches_the_server_once`.

**F3 — entregue (epoch 27).**

- *"Sair da conta" limpa o aparelho:* `CurvaOfflineData.forgetAccount`
  apaga os três bancos da conta (fila/ficha do guiado, cargas e rascunhos,
  leituras/escritas de `offline-data.js`) e o marcador de posse; o SW apaga a
  cópia da página no POST. Antes de confirmar, `workout-shell.js` conta as
  pendências pelo selo e avisa "Há N registros … ainda não enviados … serão
  apagados e não poderão ser recuperados". Sem conexão o app não deixa sair
  (só o servidor encerra a sessão; limpar só o aparelho deixaria o aluno
  logado).
- *Painel de pendências (UX de conflito unificada):* o selo virou botão;
  abre um painel com o que há em cada fila (guiado, cargas, avaliações,
  tutorial), a idade do registro mais antigo e o que o servidor recusou —
  com o lugar onde se resolve (treino guiado ou aba Cargas, que já têm UI de
  conflito). Com recusa pendente o selo diz "· revisar".
- *Telemetria de atraso:* todo envio drenado de fila (guiado, cargas,
  avaliação, onboarding) leva `X-Curva-Queued-Ms`, medido no relógio do
  aparelho; `public_workout_offline_telemetry.py` registra
  `curva_offline_sync_lag kind=… bucket=… lag_s=…` no logger
  `octobox.curva.offline` quando passa de 1 min — sem conta, slug ou valor.
- *e2e:* `test_curva_offline_signout_e2e.py` (aviso, cancelar, confirmar e
  aparelho limpo) e `test_dieta_opens_from_the_device_copy_without_network`.
  Os helpers de espera do IndexedDB moraram em `tests/e2e/curva_offline.py`.
- *Background Sync (Android) — decidido NÃO fazer.* Só tem valor se o SW
  drenar com o app fechado, e o SW não consegue: não lê o cookie CSRF, não
  tem o mapa `local_session_id → session_id` nem a UI de conflito, e o iOS
  não tem a API. A drenagem ao abrir o app, no `online` e ao voltar o foco
  cobre o caso real (o aluno abre o app ao sair da academia); o painel e a
  telemetria mostram se algo ficar preso. Reabrir só se a telemetria mostrar
  atraso grande recorrente em Android.

## 5. Riscos e decisões em aberto

| Risco / decisão | Posição recomendada |
|---|---|
| iOS sem Background Sync | aceitar: drenagem na abertura cobre o caso real (aluno reabre o app ao sair da academia) |
| iOS expurga storage de web app não instalado após ~7 dias sem uso | empurrar instalação do PWA (banner já existe) + `storage.persist()` |
| Snapshot de saúde no aparelho por 30 dias | aceitável: IndexedDB por conta + limpeza no `sair`; é o mesmo tier de exposição do outbox atual |
| Dois alunos no mesmo aparelho | já coberto pelo particionamento por escopo; a casca valida o escopo antes de hidratar |
| Duplicação na sincronização | idempotency_key em todas as escritas (servidor já tem o padrão em `record_load`) |
| Shell e página server-rendered divergirem | F1/F2 migram a renderização online para a MESMA hidratação cliente (um caminho só de render, dados do JSON) — a casca deixa de ser um segundo template |
