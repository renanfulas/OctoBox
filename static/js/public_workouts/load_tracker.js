/*
 * ARQUIVO: registro de carga do "template unico" (Onda B3 do CORDA, item 8).
 *
 * POR QUE ELE EXISTE:
 * - workout.html ja mostra a EVOLUCAO de carga (aba Historico, alimentada
 *   por load_history/one_rep_max_by_movement — ver templatetags
 *   public_workouts_extras.py::load_chart_points), mas ate aqui nao tinha
 *   como o aluno REGISTRAR a carga de hoje: so existia o endpoint HTTP
 *   (POST /renan/<slug>/carga, PublicWorkoutRecordLoadView) sem UI nenhuma
 *   chamando ele. Este arquivo e essa UI.
 * - Nao reusa static/js/public_workouts/app.js: aquele arquivo e do grid
 *   semanal client-only (.wk-input/.tp-*) das 8 paginas legadas que a
 *   Onda B3 vai apagar (item 3) — grid que nunca saia do localStorage do
 *   aparelho. Aqui o modelo e outro (backend real, um registro por data,
 *   nao uma grade fixa de 5 semanas), entao a UI tambem e outra: um input
 *   por movimento rastreado, "o que voce levantou HOJE".
 *
 * PONTOS CRITICOS (outbox em IndexedDB, item 8):
 * - Toda gravacao (clique em Salvar OU rascunho automatico em
 *   visibilitychange) primeiro entra no IndexedDB (`public-workout-outbox`,
 *   store `pending-loads`) — so DEPOIS tenta enviar. Se o envio falhar
 *   (offline, erro de rede), o registro fica no outbox e uma proxima
 *   tentativa (evento `online`, proximo load da pagina) reenvia sozinho.
 *   E o mesmo motivo de "Nenhum aluno perdeu carga" (Pronto-quando #5 da
 *   Onda B3): perder o dado seria pior que atrasar o envio.
 * - `idempotency_key` e gerada UMA VEZ, no momento em que o registro entra
 *   no outbox, e reenviada sem trocar em toda tentativa seguinte —
 *   PublicWorkoutRecordLoadView/record_load (public_workouts/services.py)
 *   usa ela pra nunca duplicar linha num reenvio. Duas gravacoes
 *   DIFERENTES (o aluno corrige o proprio numero e salva de novo) geram
 *   chaves diferentes de proposito: sao dois eventos, nao um so repetido.
 * - Limpeza no logout: ainda NAO ha rota de logout no corredor (so o
 *   cookie de posse do B0 e a sessao de login do B1, nenhum "sair"
 *   clicavel hoje) — por isso `clearOutbox` so fica exportada
 *   (`window.PublicWorkoutLoadTracker.clearOutbox`) esperando esse botao
 *   nascer, em vez de fingir que ja esta ligada a algo real.
 * - 401 (sessao de login expirou) NUNCA limpa o outbox — o registro fica
 *   guardado e tenta de novo sozinho assim que o aluno logar de novo
 *   (mesmo padrao de "sessao expirou, faca login novamente" de
 *   assessments.js, sem duplicar a logica de leitura de cookie daqui:
 *   so precisamos do redirect, nao do relatorio).
 *
 * PONTOS CRITICOS (dica de ultima carga + stepper):
 * - GET /renan/<slug>/pacote.json (PublicWorkoutPackageView, ja existe)
 *   devolve `last_top_set_by_movement` — usado so pra popular a dica "Última
 *   vez: X kg" acima do campo. 401 aqui (sem sessao ainda) so deixa a
 *   dica vazia, nunca bloqueia o registro em si (o aluno pode digitar e
 *   salvar sem nunca ter visto a dica — ela e so um atalho, nao um
 *   pre-requisito).
 * - O stepper (+/-2,5kg) edita o MESMO campo que o clique/toque direto —
 *   nao existe um segundo estado interno. Dispara o mesmo evento `input`
 *   que marca `data-dirty`, entao o rascunho automatico em
 *   visibilitychange cobre o stepper tambem, de graca.
 *
 * PONTOS CRITICOS (reps/RIR — plano curva-carga-completa-reps-rir-recorde,
 * Fase 1):
 * - O backend (record_load) ja aceitava reps/rir ha semanas; o gap era
 *   100% aqui — este arquivo nunca incluia os dois campos no payload.
 * - RIR nunca tem valor padrao nem e copiado da dica de "ultima vez"
 *   (paintHints) — inventar a percepcao de esforco do aluno e pior que
 *   nao mostrar nada. So peso/reps sao copiaveis.
 * - Parsing estrito: regex fecha o campo antes do fetch, nunca parseFloat
 *   parcial (que aceitaria "8kg" como 8). Servidor valida de novo do
 *   zero (services.py::_validate_load_values) — este arquivo NAO e a
 *   unica linha de defesa, so evita a viagem de rede pro caso comum.
 * - Trocar de exercicio (wireSubstitutePills) limpa peso/reps/RIR do
 *   widget — carregar 60kg de um movimento de barra pra um de halteres
 *   nao significa nada (achado real: o comportamento anterior deixava o
 *   valor antigo no campo depois da troca).
 * - Rascunho (store `drafts`, chave composta plano+movimento+data,
 *   IndexedDB v2) e' SEPARADO da outbox confirmada (`pending-loads`):
 *   editar (ou o auto-save de visibilitychange) so grava rascunho local,
 *   nunca um POST de "realizado". Só o clique explícito em Salvar
 *   promove rascunho -> outbox confirmada (com idempotency_key gerada
 *   na hora da promoção) e apaga o rascunho correspondente. Ao reabrir a
 *   pagina/trocar de exercicio, rascunho local prevalece sobre o eco
 *   "confirmado hoje" que o servidor pre-preencheu (ver hydrateDraft).
 * - LIMITACAO CONHECIDA, NAO RESOLVIDA NESTA RODADA: o rascunho hoje e'
 *   por (plano, movimento, data) no dispositivo — nao por CONTA. Em
 *   aparelho compartilhado por duas contas, um rascunho deixado por uma
 *   conta pode aparecer pra outra que logar depois no mesmo plano/dia.
 *   Fechar isso de verdade exige o backend expor um identificador
 *   estavel de conta pro cliente (pacote.json nao devolve isso hoje) pra
 *   namespacear a chave — decisao de produto, nao so codigo.
 */

(function () {
  'use strict';

  var body = document.body;
  var DB_NAME = 'public-workout-outbox';
  var DB_VERSION = 2; // v2: acrescenta o store de rascunho (ver DRAFT_STORE_NAME)
  var STORE_NAME = 'pending-loads';
  var DRAFT_STORE_NAME = 'drafts';
  var DRAFT_DEBOUNCE_MS = 600;

  function planSlug() {
    return body.getAttribute('data-plan-slug') || '';
  }

  function pad2(n) {
    return n < 10 ? '0' + n : '' + n;
  }

  function todayIso() {
    var d = new Date();
    return d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate());
  }

  function uuid() {
    if (window.crypto && window.crypto.randomUUID) { return window.crypto.randomUUID(); }
    // Fallback pra navegador sem crypto.randomUUID (raro, mas o corredor
    // roda em aparelho de aluno variado demais pra assumir suporte).
    return 'load-' + Date.now() + '-' + Math.random().toString(16).slice(2);
  }

  // Mesmo padrao de assessments.js::getCookie/postJson — nao importa aquele
  // arquivo direto porque nem toda pagina que carrega load_tracker.js
  // necessariamente carrega assessments.js (abas independentes).
  function getCookie(name) {
    var parts = (document.cookie || '').split(';');
    for (var i = 0; i < parts.length; i++) {
      var part = parts[i].trim();
      if (part.indexOf(name + '=') === 0) {
        return decodeURIComponent(part.slice(name.length + 1));
      }
    }
    return '';
  }

  function postJson(url, payload) {
    return window.fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: JSON.stringify(payload || {}),
    }).then(function (response) {
      return response.text().then(function (text) {
        var data = {};
        if (text) {
          try { data = JSON.parse(text); } catch (e) { /* corpo nao-JSON */ }
        }
        return { ok: response.ok, status: response.status, data: data };
      });
    });
  }

  /* ══ OUTBOX (IndexedDB) ═══════════════════════════════════════ */

  function openDb() {
    return new Promise(function (resolve, reject) {
      if (!window.indexedDB) { reject(new Error('sem IndexedDB')); return; }
      var request = window.indexedDB.open(DB_NAME, DB_VERSION);
      request.onupgradeneeded = function () {
        var db = request.result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME, { keyPath: 'idempotency_key' });
        }
        // v2 (plano curva-carga-completa-reps-rir-recorde, §3.2): store
        // separado pra rascunho -- chave composta (plano/movimento/data)
        // porque um rascunho e' por combinacao dessas tres coisas, nao
        // por idempotency_key (que so nasce quando o rascunho e'
        // promovido pra confirmado, no clique em Salvar).
        if (!db.objectStoreNames.contains(DRAFT_STORE_NAME)) {
          db.createObjectStore(DRAFT_STORE_NAME, { keyPath: ['plan_slug', 'movement_slug', 'performed_on'] });
        }
      };
      request.onblocked = function () {
        // Outra aba da mesma origem ainda tem a versao 1 aberta -- nao
        // forca o upgrade (fecharia a conexao da outra aba no meio do
        // uso). A proxima tentativa (reload, ou a outra aba fechando)
        // resolve sozinha; nunca perde rascunho/outbox por isso.
        reject(new Error('upgrade do IndexedDB bloqueado por outra aba'));
      };
      request.onsuccess = function () {
        var db = request.result;
        db.onversionchange = function () { db.close(); };
        resolve(db);
      };
      request.onerror = function () { reject(request.error); };
    });
  }

  function withStore(storeName, mode, fn) {
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(storeName, mode);
        var store = tx.objectStore(storeName);
        var result = fn(store);
        tx.oncomplete = function () { resolve(result); };
        tx.onerror = function () { reject(tx.error); };
      });
    });
  }

  function queueEntry(entry) {
    return withStore(STORE_NAME, 'readwrite', function (store) { store.put(entry); return entry; });
  }

  function removeEntry(idempotencyKey) {
    return withStore(STORE_NAME, 'readwrite', function (store) { store.delete(idempotencyKey); });
  }

  function listEntries() {
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(STORE_NAME, 'readonly');
        var request = tx.objectStore(STORE_NAME).getAll();
        request.onsuccess = function () { resolve(request.result || []); };
        request.onerror = function () { reject(request.error); };
      });
    });
  }

  function clearOutbox() {
    return withStore(STORE_NAME, 'readwrite', function (store) { store.clear(); });
  }

  /* ══ RASCUNHO (IndexedDB, store separado da outbox confirmada) ══ */

  function draftKey(widget) {
    return {
      plan_slug: planSlug(),
      movement_slug: widget.getAttribute('data-movement-slug'),
      performed_on: todayIso(),
    };
  }

  function putDraft(widget, weightKg, reps, rir) {
    var key = draftKey(widget);
    return withStore(DRAFT_STORE_NAME, 'readwrite', function (store) {
      store.put({
        plan_slug: key.plan_slug,
        movement_slug: key.movement_slug,
        performed_on: key.performed_on,
        weight_kg: weightKg,
        reps: reps,
        rir: rir,
        saved_at: Date.now(),
      });
    });
  }

  function deleteDraft(widget) {
    var key = draftKey(widget);
    return withStore(DRAFT_STORE_NAME, 'readwrite', function (store) {
      store.delete([key.plan_slug, key.movement_slug, key.performed_on]);
    });
  }

  function getDraft(widget) {
    var key = draftKey(widget);
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(DRAFT_STORE_NAME, 'readonly');
        var request = tx.objectStore(DRAFT_STORE_NAME).get([key.plan_slug, key.movement_slug, key.performed_on]);
        request.onsuccess = function () { resolve(request.result || null); };
        request.onerror = function () { reject(request.error); };
      });
    });
  }

  function clearDrafts() {
    return withStore(DRAFT_STORE_NAME, 'readwrite', function (store) { store.clear(); });
  }

  // Persiste o rascunho ATUAL do widget (ou apaga, se os campos voltaram
  // a vazio). Nunca falha "para cima" -- erro de IndexedDB aqui so
  // significa que o rascunho local nao ficou salvo entre reloads, nunca
  // bloqueia a edicao em si.
  function persistDraftFromWidget(widget) {
    var weightParsed = parseWeightField(widget.querySelector('[data-workout-load-field]'));
    var repsParsed = parseRepsField(widget.querySelector('[data-workout-reps-field]'));
    if (!weightParsed.ok || !repsParsed.ok) { return Promise.resolve(); }
    if (weightParsed.value === null && repsParsed.value === null) {
      return deleteDraft(widget).catch(function () {});
    }
    return putDraft(widget, weightParsed.value, repsParsed.value, getRirValue(widget)).catch(function () {});
  }

  function scheduleDraftSave(widget) {
    if (widget._draftTimer) { window.clearTimeout(widget._draftTimer); }
    widget._draftTimer = window.setTimeout(function () {
      widget._draftTimer = null;
      persistDraftFromWidget(widget);
    }, DRAFT_DEBOUNCE_MS);
  }

  function flushPendingDraft(widget) {
    if (widget._draftTimer) { window.clearTimeout(widget._draftTimer); widget._draftTimer = null; }
    return persistDraftFromWidget(widget);
  }

  // Ao reabrir a pagina/trocar de exercicio: rascunho local prevalece
  // sobre o eco "confirmado hoje" que o servidor ja pre-preencheu (plano
  // §1.2 — "rascunho do movimento/data prevalece ao reabrir").
  function hydrateDraft(widget) {
    getDraft(widget).then(function (draft) {
      if (!draft) { return; }
      var weightField = widget.querySelector('[data-workout-load-field]');
      var repsField = widget.querySelector('[data-workout-reps-field]');
      if (draft.weight_kg !== null && draft.weight_kg !== undefined && weightField) {
        weightField.value = draft.weight_kg;
        markDirty(weightField);
      }
      if (draft.reps !== null && draft.reps !== undefined && repsField) {
        repsField.value = draft.reps;
        markDirty(repsField);
      }
      if (draft.rir !== null && draft.rir !== undefined) {
        var rirKey = String(draft.rir);
        var label = RIR_LABELS[rirKey] || ('RIR ' + fmtNumber(draft.rir));
        setRirSelection(widget, rirKey, label);
        var otherField = widget.querySelector('[data-workout-rir-other-field]');
        var exactPill = widget.querySelector('[data-rir-value="' + rirKey + '"]');
        if (!exactPill && otherField) { otherField.hidden = false; otherField.value = rirKey; }
      }
      setStatus(widget, 'Rascunho neste aparelho, após escrita local', false);
      updateSaveLabel(widget);
    }).catch(function () { /* sem IndexedDB, ou leitura falhou -- silencioso, mesmo padrao do resto do arquivo */ });
  }

  // Widget(s) ATIVOS pro movimento de uma entrada drenada -- querySelectorAll
  // porque o mesmo movement_slug pode aparecer em mais de uma aba/dia
  // (mesmo padrao de paintHints, que tambem itera todos).
  function widgetsForMovement(movementSlug) {
    return document.querySelectorAll(
      '[data-workout-load-input][data-movement-slug="' + movementSlug + '"]'
    );
  }

  // Reporta o resultado de UMA entrada drenada pro(s) widget(s) daquele
  // movimento, se estiverem na pagina agora. `isBatch` (mais de uma
  // entrada nesta rodada de drenagem) escolhe o tom: uma unica entrada
  // sincronizando ainda recebe o selo normal (§6.3: "confirmacao com
  // exercicio ativo atualiza seu recibo"); varias de uma vez agrupam num
  // aviso calmo so' em texto, sem repetir a animacao pra cada uma
  // ("confirmacao tardia agrupa 'Registros sincronizados' ... sem
  // sequencia de celebracoes antigas").
  function reportDrainedEntry(entry, responseData, isBatch) {
    var widgets = widgetsForMovement(entry.movement_slug);
    if (!widgets.length) { return; }
    var achievement = responseData && responseData.achievement;
    widgets.forEach(function (widget) {
      rememberTodayEntry(widget, entry);
      if (isBatch) {
        var extra = achievement
          ? (' · nova maior carga (+' + fmtNumber(achievement.delta_kg) + ' kg sobre seu recorde anterior)')
          : '';
        setStatus(widget, 'Registros sincronizados — ' + describeEntry(entry) + extra, false);
        // Marca como "ja celebrado" sem tocar no selo visual -- se uma
        // retentativa isolada desta MESMA chave chegar depois (ex.: outra
        // aba), ela nao reabre o selo pra algo que ja foi resumido aqui.
        celebratedOperationKeys[entry.idempotency_key] = true;
        return;
      }
      setStatus(widget, 'Registro sincronizado — ' + describeEntry(entry), false);
      pulseSuccess(widget);
      showAchievementOnce(widget, entry.idempotency_key, achievement, entry);
    });
  }

  // Drena o outbox: tenta reenviar cada registro pendente. 401 (sessao
  // expirada) e erro de rede param a drenagem inteira (a proxima tentativa
  // resolve sozinha, nao adianta insistir nos seguintes agora); 400 (dado
  // invalido — nao deveria acontecer, mas nao pode travar o outbox pra
  // sempre) descarta so aquele registro e segue pros outros.
  function drainOutbox() {
    var slug = planSlug();
    if (!slug || !navigator.onLine) { return Promise.resolve(); }

    return listEntries().then(function (entries) {
      var isBatch = entries.length > 1;
      var chain = Promise.resolve();
      entries.forEach(function (entry) {
        chain = chain.then(function () {
          return postJson('/renan/' + slug + '/carga', entry).then(function (result) {
            if (result.ok) {
              reportDrainedEntry(entry, result.data, isBatch);
              return removeEntry(entry.idempotency_key);
            }
            if (result.status === 400) { return removeEntry(entry.idempotency_key); }
            // 409 (Fase 3 — correcao com alvo ja corrigido por outra
            // operacao) e' permanente, nunca transitorio: retentativa
            // infinita bloquearia o resto da fila pra sempre. Descarta.
            // LIMITACAO CONHECIDA: se o aluno editou duas vezes offline
            // antes de reconectar, a segunda correcao enfileirada pode
            // colidir com a primeira quando a fila drenar em ordem e ser
            // descartada aqui -- perde silenciosamente a segunda edicao
            // em vez de reabrir como rascunho. Cenario raro (offline +
            // duas edicoes em sequencia); resolver direito exigiria a
            // fila devolver resultado por item pro chamador, nao so'
            // drenar-e-esquecer.
            if (result.status === 409) { return removeEntry(entry.idempotency_key); }
            return Promise.reject(new Error('drain interrompido, status ' + result.status));
          });
        });
      });
      return chain.catch(function () { /* proxima tentativa (online/load) resolve */ });
    });
  }

  /* ══ DICA DE ULTIMA CARGA ═══════════════════════════════════════ */

  function fetchLastLoadByMovement() {
    var slug = planSlug();
    if (!slug) { return Promise.resolve({}); }
    return window.fetch('/renan/' + slug + '/pacote.json', { credentials: 'same-origin' })
      .then(function (response) { return response.ok ? response.json() : {}; })
      .then(function (data) { return data.last_top_set_by_movement || {}; })
      .catch(function () { return {}; });
  }

  function paintHints(lastLoadByMovement) {
    document.querySelectorAll('[data-workout-load-input]').forEach(function (widget) {
      var slug = widget.getAttribute('data-movement-slug');
      var entry = lastLoadByMovement[slug];
      var hint = widget.querySelector('[data-workout-load-hint]');
      var weightField = widget.querySelector('[data-workout-load-field]');
      var repsField = widget.querySelector('[data-workout-reps-field]');
      if (!entry || !hint) { return; }

      var hasWeight = entry.weight_kg !== null && entry.weight_kg !== undefined;
      var hasReps = entry.reps !== null && entry.reps !== undefined;
      if (!hasWeight && !hasReps) { return; }

      // RIR nunca entra na dica/copia (ver docstring do arquivo) — so
      // peso/reps sao ecoados, nunca esforco.
      var label;
      if (hasWeight && hasReps) { label = 'Usar ' + entry.weight_kg + ' kg × ' + entry.reps; }
      else if (hasWeight) { label = 'Usar ' + entry.weight_kg + ' kg'; }
      else { label = 'Usar ' + entry.reps + ' reps'; }

      hint.textContent = label + ' — toque pra usar';
      hint.addEventListener('click', function () {
        if (hasWeight && weightField) { weightField.value = entry.weight_kg; markDirty(weightField); }
        if (hasReps && repsField) { repsField.value = entry.reps; markDirty(repsField); }
        updateSaveLabel(widget);
      });
    });
  }

  /* ══ UI POR MOVIMENTO ═══════════════════════════════════════════ */

  function setStatus(widget, text, isError) {
    var status = widget.querySelector('[data-workout-load-status]');
    if (!status) { return; }
    status.textContent = text;
    status.classList.toggle('workout-load-input__status--error', !!isError);
  }

  function rememberTodayEntry(widget, entry) {
    if (!widget || !entry || !entry.idempotency_key) { return; }
    var rolePrefix = entry.set_role === 'warmup' ? 'warmup' : 'top-set';
    var roleAttribute = 'data-today-' + rolePrefix + '-idempotency-key';
    widget.setAttribute(roleAttribute, entry.idempotency_key);
    widget.setAttribute('data-today-idempotency-key', entry.idempotency_key);
    ['weight', 'reps', 'rir'].forEach(function (fieldName) {
      var value = entry[fieldName === 'weight' ? 'weight_kg' : fieldName];
      var attribute = 'data-today-' + rolePrefix + '-' + fieldName;
      if (value === null || value === undefined || value === '') {
        widget.removeAttribute(attribute);
      } else {
        widget.setAttribute(attribute, String(value));
      }
    });
  }

  function buildEntryFromWidget(widget, weightKg, reps, rir) {
    // Plano curva-grafico-hierarquia-e-set-role.md (§2.3.6/§7.10):
    // set_role SEMPRE presente no payload, nunca omitido -- e' o que
    // garante que o cliente novo nunca mais cai no caso "chave ausente"
    // (legacy_unknown) que o protocolo da view reserva pra clientes
    // antigos/outbox pre-deploy.
    var warmupToggle = widget.querySelector('[data-workout-load-warmup-toggle]');
    var entry = {
      idempotency_key: uuid(),
      movement_slug: widget.getAttribute('data-movement-slug'),
      program_id: widget.getAttribute('data-program-id') || '',
      weight_kg: weightKg,
      reps: reps,
      rir: rir,
      set_role: (warmupToggle && warmupToggle.checked) ? 'warmup' : 'top_set',
      performed_on: todayIso(),
    };
    // Fase 3 do plano curva-carga-completa-reps-rir-recorde (§4.2): ja
    // existe um registro ATIVO pra este movimento hoje -- "Salvar" o
    // corrige em vez de criar uma segunda linha pro mesmo dia (o widget
    // atual so' modela "um registro por movimento por dia"; ver docstring
    // do arquivo/plano §7 pro modo "varias series por dia", que e' um
    // esforco separado). set_role acima e' ignorado pelo servidor nesse
    // caminho -- correct_load herda o papel do ALVO, nunca do payload.
    var supersedesKey = widget.getAttribute('data-today-idempotency-key');
    if (supersedesKey) { entry.supersedes_idempotency_key = supersedesKey; }
    return entry;
  }

  function syncCorrectionTargetForRole(widget) {
    var warmupToggle = widget.querySelector('[data-workout-load-warmup-toggle]');
    var rolePrefix = (warmupToggle && warmupToggle.checked) ? 'warmup' : 'top-set';
    var roleAttribute = 'data-today-' + rolePrefix + '-idempotency-key';
    var roleKey = widget.getAttribute(roleAttribute);
    if (roleKey) {
      widget.setAttribute('data-today-idempotency-key', roleKey);
    } else {
      widget.removeAttribute('data-today-idempotency-key');
    }

    var weightField = widget.querySelector('[data-workout-load-field]');
    var repsField = widget.querySelector('[data-workout-reps-field]');
    var weight = widget.getAttribute('data-today-' + rolePrefix + '-weight');
    var reps = widget.getAttribute('data-today-' + rolePrefix + '-reps');
    if (weightField) {
      weightField.value = weight || '';
      weightField.removeAttribute('data-dirty');
    }
    if (repsField) {
      repsField.value = reps || '';
      repsField.removeAttribute('data-dirty');
    }

    var rir = widget.getAttribute('data-today-' + rolePrefix + '-rir');
    var rirPicker = widget.querySelector('[data-workout-rir-picker]');
    var rirValue = rir === null ? null : parseFloat(rir);
    var rirLabel = rirValue === null || !isFinite(rirValue)
      ? ''
      : (RIR_LABELS[String(rirValue)] || ('RIR ' + fmtNumber(rirValue)));
    setRirSelection(widget, rirValue !== null && isFinite(rirValue) ? rirValue : null, rirLabel);
    if (rirPicker) {
      if (rir === null) { rirPicker.removeAttribute('data-today-rir'); }
      else { rirPicker.setAttribute('data-today-rir', rir); }
    }
    var otherRir = widget.querySelector('[data-workout-rir-other-field]');
    if (otherRir) {
      var hasQuickChoice = rir !== null && widget.querySelector('[data-rir-value="' + String(rirValue) + '"]');
      otherRir.value = rir !== null && !hasQuickChoice ? rir : '';
      otherRir.hidden = !rir || !!hasQuickChoice;
    }
    var effort = widget.querySelector('[data-workout-effort]');
    if (effort) { effort.open = rir !== null; }
    updateSaveLabel(widget);
  }

  function pulseSuccess(widget) {
    widget.classList.add('workout-load-input--saved');
    window.setTimeout(function () { widget.classList.remove('workout-load-input--saved'); }, 1200);
  }

  function fmtNumber(value) {
    return (Math.round(value * 100) / 100).toString().replace('.', ',');
  }

  // Parsing estrito: regex fecha o formato ANTES de qualquer parseFloat,
  // pra nunca aceitar "8kg"/"1,2,3" como numero parcial. Campo vazio e
  // valido (significa "nao informado", devolve value:null) — so o valor
  // *preenchido e invalido* reprova (ok:false).
  function parseWeightField(field) {
    if (!field || !field.value || !field.value.trim()) { return { ok: true, value: null }; }
    var raw = field.value.trim().replace(',', '.');
    if (!/^\d+(\.\d+)?$/.test(raw)) { return { ok: false, value: null }; }
    var value = parseFloat(raw);
    if (!isFinite(value) || value < 0) { return { ok: false, value: null }; }
    return { ok: true, value: value };
  }

  function parseRepsField(field) {
    if (!field || !field.value || !field.value.trim()) { return { ok: true, value: null }; }
    var raw = field.value.trim();
    if (!/^\d+$/.test(raw)) { return { ok: false, value: null }; }
    var value = parseInt(raw, 10);
    if (value < 1 || value > 999) { return { ok: false, value: null }; }
    return { ok: true, value: value };
  }

  function getRirValue(widget) {
    var picker = widget.querySelector('[data-workout-rir-picker]');
    if (!picker) { return null; }
    var selected = picker.getAttribute('data-rir-selected');
    if (selected === null || selected === '') { return null; }
    var value = parseFloat(selected);
    return isFinite(value) ? value : null;
  }

  var RIR_LABELS = {
    '0': 'Não faria outra repetição',
    '1': 'Ainda faria 1 repetição',
    '2': 'Ainda faria 2 repetições',
    '3': 'Ainda faria 3 repetições',
    '4': 'Ainda faria 4 ou mais repetições',
  };

  function setRirSelection(widget, value, label) {
    var picker = widget.querySelector('[data-workout-rir-picker]');
    var summaryValue = widget.querySelector('[data-workout-effort-value]');
    if (!picker) { return; }
    if (value === null) {
      picker.removeAttribute('data-rir-selected');
    } else {
      picker.setAttribute('data-rir-selected', String(value));
    }
    if (summaryValue) { summaryValue.textContent = label || ''; }
    picker.querySelectorAll('[data-rir-value]').forEach(function (pill) {
      var isMatch = value !== null && pill.getAttribute('data-rir-value') === String(value);
      pill.classList.toggle('is-selected', isMatch);
      pill.setAttribute('aria-checked', isMatch ? 'true' : 'false');
    });
  }

  function wireEffortDisclosure(widget) {
    var picker = widget.querySelector('[data-workout-rir-picker]');
    if (!picker) { return; }
    var otherToggle = widget.querySelector('[data-workout-rir-other-toggle]');
    var otherField = widget.querySelector('[data-workout-rir-other-field]');
    var clearBtn = widget.querySelector('[data-workout-rir-clear]');

    picker.querySelectorAll('[data-rir-value]').forEach(function (pill) {
      pill.addEventListener('click', function () {
        var value = pill.getAttribute('data-rir-value');
        setRirSelection(widget, value, RIR_LABELS[value] || ('RIR ' + value));
        if (otherField) { otherField.value = ''; otherField.hidden = true; }
        scheduleDraftSave(widget);
      });
    });
    if (otherToggle && otherField) {
      otherToggle.addEventListener('click', function () {
        otherField.hidden = !otherField.hidden;
        if (!otherField.hidden) { otherField.focus(); }
      });
      otherField.addEventListener('input', function () {
        var raw = otherField.value.trim().replace(',', '.');
        if (!raw) { return; }
        var value = parseFloat(raw);
        if (!isFinite(value) || value < 0 || value > 99.9) { return; }
        setRirSelection(widget, String(value), 'RIR ' + fmtNumber(value));
        scheduleDraftSave(widget);
      });
    }
    // Hidrata a selecao com o RIR ja salvo hoje (todays_logged_rir,
    // renderizado no atributo data-today-rir pelo servidor) -- se cair
    // exato num atalho, marca o botao; senao (ex. 1.5), abre "outro
    // valor" ja preenchido em vez de deixar a pilula errada marcada.
    var todayRirRaw = picker.getAttribute('data-today-rir');
    if (todayRirRaw) {
      // O servidor pode renderizar "2.0" (float serializado) pra um RIR
      // que na verdade e' o atalho exato "2" -- normaliza antes de
      // comparar, senao "2.0" nunca bate com data-rir-value="2" e cai
      // sempre em "outro valor" por engano.
      var todayRirNum = parseFloat(todayRirRaw);
      var todayRir = isFinite(todayRirNum) ? String(todayRirNum) : todayRirRaw;
      var exactPill = picker.querySelector('[data-rir-value="' + todayRir + '"]');
      if (exactPill) {
        setRirSelection(widget, todayRir, RIR_LABELS[todayRir] || ('RIR ' + todayRir));
      } else if (otherField) {
        otherField.hidden = false;
        otherField.value = todayRir;
        setRirSelection(widget, todayRir, 'RIR ' + todayRir.replace('.', ','));
      }
    }
    if (clearBtn) {
      clearBtn.addEventListener('click', function () {
        setRirSelection(widget, null, '');
        if (otherField) { otherField.value = ''; otherField.hidden = true; }
        scheduleDraftSave(widget);
      });
    }
  }

  // CTA reflete os dados presentes (plano §1.3) — nunca um "Salvar" cego
  // que esconde o que vai ser gravado. Desabilita quando nao ha peso NEM
  // reps: uma linha sem nenhum dos dois nao registra nada de verdade
  // (essa exigencia fica so no cliente — o servico preserva um caso real
  // de movimento isometrico sem peso/reps que ja existia antes deste
  // widget, ver services.py::_validate_load_values).
  function updateSaveLabel(widget) {
    var saveBtn = widget.querySelector('[data-workout-load-save]');
    if (!saveBtn) { return; }
    var weightParsed = parseWeightField(widget.querySelector('[data-workout-load-field]'));
    var repsParsed = parseRepsField(widget.querySelector('[data-workout-reps-field]'));
    var weight = weightParsed.ok ? weightParsed.value : null;
    var reps = repsParsed.ok ? repsParsed.value : null;
    var label;
    if (weight !== null && reps !== null) { label = 'Salvar ' + fmtNumber(weight) + ' kg × ' + reps; }
    else if (weight !== null) { label = 'Salvar ' + fmtNumber(weight) + ' kg'; }
    else if (reps !== null) { label = 'Salvar ' + reps + ' reps'; }
    else { label = 'Salvar'; }
    saveBtn.textContent = label;
    saveBtn.disabled = weight === null && reps === null;
  }

  function describeEntry(entry) {
    var parts = [];
    if (entry.weight_kg !== null) { parts.push(fmtNumber(entry.weight_kg) + ' kg'); }
    if (entry.reps !== null) { parts.push(entry.reps + ' reps'); }
    if (entry.rir !== null) { parts.push('RIR ' + fmtNumber(entry.rir)); }
    return parts.join(' · ');
  }

  /* ══ CELEBRAÇÃO DE RECORDE (Fase 4, §6) ══════════════════════════
   * O SERVIDOR decide se houve recorde (services.py::record_load/
   * correct_load, dentro da mesma transacao que grava a linha) -- este
   * arquivo so' EXIBE o que veio em result.data.achievement, nunca
   * calcula nada por conta propria (offline nunca teria como saber o
   * "recorde anterior" de verdade sem consultar o servidor).
   */

  // Por idempotency_key, nunca por movimento -- uma retentativa (rede
  // duplicada, drainOutbox concorrente) que devolve o MESMO resultado
  // persistido nao pode reanimar o selo uma segunda vez (plano: "cliente
  // deduplica feedback pela chave da operacao").
  var celebratedOperationKeys = {};

  // Sempre chamada em toda gravacao bem-sucedida (com ou sem recorde):
  // limpa o selo de uma gravacao ANTERIOR quando esta nao traz recorde
  // nenhum -- "correcao posterior invalida selo nas leituras futuras"
  // (corrigir 100kg pra 80kg nao pode deixar o troféu de 100kg exibido).
  function updateAchievementBadge(widget, achievement, entry) {
    var el = widget.querySelector('[data-workout-load-achievement]');
    if (!el) { return; }
    if (!achievement) {
      el.hidden = true;
      el.classList.remove('workout-load-input__achievement--visible');
      el.textContent = '';
      return;
    }
    var label = widget.getAttribute('data-movement-label') || '';
    var detail = fmtNumber(entry.weight_kg) + ' kg';
    if (entry.reps !== null && entry.reps !== undefined) { detail += ' × ' + entry.reps + ' reps'; }
    var delta = achievement.delta_kg;
    var deltaText = (typeof delta === 'number') ? ('+' + fmtNumber(delta) + ' kg sobre seu recorde anterior.') : 'novo recorde.';
    el.textContent = '';
    var title = document.createElement('strong');
    title.textContent = 'Nova maior carga' + (label ? (' em ' + label) : '') + '.';
    var body = document.createElement('span');
    body.textContent = detail + ' · ' + deltaText;
    el.appendChild(title);
    el.appendChild(body);
    el.hidden = false;
    el.classList.add('workout-load-input__achievement--visible');
  }

  // Guarda de dedup em torno da ANIMACAO/selo em si (updateAchievementBadge
  // sozinho e' idempotente, mas ainda assim so' deve ser chamado uma vez
  // por operacao pra nao reprocessar o DOM sem motivo numa segunda
  // confirmacao da mesma chave).
  function showAchievementOnce(widget, idempotencyKey, achievement, entry) {
    if (celebratedOperationKeys[idempotencyKey]) { return; }
    celebratedOperationKeys[idempotencyKey] = true;
    updateAchievementBadge(widget, achievement, entry);
  }

  // Guarda localmente (fila offline) e reporta -- caminho de fallback
  // pra quando o envio direto (saveWidget) nao rola (offline, erro de
  // rede, 5xx). Otimista de proposito (mesmo espirito do resto do outbox):
  // assume que vai dar certo na proxima tentativa, nunca bloqueia a
  // edicao esperando confirmacao do servidor.
  function queueOfflineAndReport(widget, entry, weightField, repsField) {
    return queueEntry(entry)
      .then(function () {
        if (weightField) { weightField.removeAttribute('data-dirty'); }
        if (repsField) { repsField.removeAttribute('data-dirty'); }
        setStatus(widget, 'Guardado neste aparelho · envio pendente — ' + describeEntry(entry), false);
        pulseSuccess(widget);
        return deleteDraft(widget).catch(function () {});
      })
      .catch(function () {
        setStatus(widget, 'Não foi possível guardar o registro neste aparelho. Tente novamente.', true);
      });
  }

  function saveWidget(widget) {
    // Acha real, nao hipotetico: toque duplo (comum no celular, principalmente
    // com qualquer engasgo de tela) gerava DOIS idempotency_key diferentes --
    // a idempotencia protege reenvio da MESMA tentativa pela rede, nunca
    // protegeu duas tentativas reais e distintas. Desabilitar o botao durante
    // o salvamento fecha essa janela na origem, sem precisar de debounce nem
    // de nada no backend.
    var saveBtn = widget.querySelector('[data-workout-load-save]');
    if (saveBtn && saveBtn.disabled) { return; }

    var weightField = widget.querySelector('[data-workout-load-field]');
    var repsField = widget.querySelector('[data-workout-reps-field]');
    var weightParsed = parseWeightField(weightField);
    var repsParsed = parseRepsField(repsField);

    if (!weightParsed.ok) {
      setStatus(widget, 'Peso inválido — confira o valor antes de salvar.', true);
      return;
    }
    if (!repsParsed.ok) {
      setStatus(widget, 'Repetições inválidas — use um número inteiro de 1 a 999.', true);
      return;
    }
    if (weightParsed.value === null && repsParsed.value === null) {
      setStatus(widget, 'Informe ao menos o peso ou as repetições.', true);
      return;
    }

    var entry = buildEntryFromWidget(widget, weightParsed.value, repsParsed.value, getRirValue(widget));
    var slug = planSlug();
    setStatus(widget, 'Salvando…', false);
    if (saveBtn) { saveBtn.disabled = true; }

    // Envio DIRETO primeiro (nao pela fila) -- e' o unico jeito de saber
    // de verdade se uma correcao deu 409 (alvo ja corrigido em outro
    // lugar) em vez de assumir sucesso so' porque a entrada saiu do
    // IndexedDB (drainOutbox generico nao devolve resultado por item).
    var direct = (!slug || !navigator.onLine)
      ? Promise.resolve({ ok: false, status: 0, data: {} })
      : postJson('/renan/' + slug + '/carga', entry).catch(function () { return { ok: false, status: 0, data: {} }; });

    direct
      .then(function (result) {
        if (result.ok) {
          if (weightField) { weightField.removeAttribute('data-dirty'); }
          if (repsField) { repsField.removeAttribute('data-dirty'); }
          // A mesma chave que ja enviamos passa a ser "a de hoje" --
          // nao precisa reconsultar o servidor pra saber isso.
          rememberTodayEntry(widget, entry);
          var wasCorrection = !!entry.supersedes_idempotency_key;
          setStatus(widget, (wasCorrection ? 'Registro corrigido — ' : 'Registro salvo — ') + describeEntry(entry), false);
          pulseSuccess(widget);
          // Offline nunca recebe trofeu otimista (§6.3) -- este e' o
          // caminho de POST DIRETO confirmado pelo servidor, entao mostrar
          // o selo aqui e' seguro; queueOfflineAndReport (abaixo) nunca
          // chama isto.
          showAchievementOnce(widget, entry.idempotency_key, result.data && result.data.achievement, entry);
          // Sabemos que a conexao esta boa agora -- aproveita pra tentar
          // esvaziar qualquer coisa que ainda esteja pendente de antes
          // (fire-and-forget, nao atrasa o feedback desta gravacao).
          drainOutbox();
          return deleteDraft(widget).catch(function () {});
        }
        if (result.status === 409) {
          setStatus(widget, 'Este registro já foi atualizado em outro lugar — atualize a página para continuar.', true);
          return;
        }
        if (result.status === 400) {
          var message = (result.data && result.data.error) || 'Dados inválidos — confira os valores antes de salvar.';
          setStatus(widget, message, true);
          return;
        }
        if (result.status === 401) {
          setStatus(widget, 'Sessão expirada — entre novamente para salvar. O que você digitou continua guardado.', true);
          return persistDraftFromWidget(widget);
        }
        // Offline, erro de rede, ou 5xx -- unicos casos onde vale
        // enfileirar pra tentar de novo depois (400/401/409 sao
        // definitivos, retentar nao mudaria o resultado).
        return queueOfflineAndReport(widget, entry, weightField, repsField);
      })
      .then(function () {
        if (saveBtn) { saveBtn.disabled = false; }
        updateSaveLabel(widget);
      });
  }

  function markDirty(field) {
    field.setAttribute('data-dirty', '1');
  }

  // Steps do valor atual do campo (ou 0, se vazio) — nunca deixa negativo,
  // mesmo padrao de min="0" do <input type=number>.
  function stepField(field, delta) {
    var current = field.value ? parseFloat(field.value.replace(',', '.')) : 0;
    if (isNaN(current)) { current = 0; }
    var next = Math.max(0, Math.round((current + delta) * 100) / 100);
    field.value = next;
    markDirty(field);
  }

  // Reps nunca vira 0 a partir do vazio: "-" num campo ainda nao
  // preenchido nao cria dado (plano §1.3) — so "+" comeca a contagem, do
  // incremento pra frente.
  function stepReps(field, delta) {
    if (!field) { return; }
    if (!field.value && delta < 0) { return; }
    var current = field.value ? parseInt(field.value, 10) : 0;
    if (isNaN(current)) { current = 0; }
    var next = Math.max(1, current + delta);
    field.value = next;
    markDirty(field);
  }

  /* ══ CALCULADORA DE ANILHAS (plano curva-carga-completa..., §5) ═══ */
  // So' aparece no widget quando o template ja confirmou os dois
  // metadados curados (movement_shows_plate_calculator) -- este modulo
  // so' cuida da MATEMATICA e da config local, nunca decide SE aparece.

  var PLATE_STORAGE_KEY = 'curva-plate-config';
  var DEFAULT_PLATE_SIZES = [20, 15, 10, 5, 2.5, 1.25];
  var DEFAULT_PAIRS_PER_SIZE = 4;
  var DEFAULT_BAR_KG = 20;

  function safeLocalStorage() {
    try { return window.localStorage; } catch (e) { return null; }
  }

  function defaultPairs() {
    var pairs = {};
    DEFAULT_PLATE_SIZES.forEach(function (size) { pairs[size] = DEFAULT_PAIRS_PER_SIZE; });
    return pairs;
  }

  function loadPlateConfig() {
    var ls = safeLocalStorage();
    if (!ls) { return { barKg: DEFAULT_BAR_KG, pairs: defaultPairs() }; }
    try {
      var raw = ls.getItem(PLATE_STORAGE_KEY);
      if (!raw) { return { barKg: DEFAULT_BAR_KG, pairs: defaultPairs() }; }
      var parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== 'object') { return { barKg: DEFAULT_BAR_KG, pairs: defaultPairs() }; }
      return {
        barKg: isFinite(parsed.barKg) ? parsed.barKg : DEFAULT_BAR_KG,
        pairs: parsed.pairs && typeof parsed.pairs === 'object' ? parsed.pairs : defaultPairs(),
      };
    } catch (e) { return { barKg: DEFAULT_BAR_KG, pairs: defaultPairs() }; }
  }

  function savePlateConfig(config) {
    var ls = safeLocalStorage();
    if (!ls) { return; }
    try { ls.setItem(PLATE_STORAGE_KEY, JSON.stringify(config)); } catch (e) {}
  }

  // Algoritmo deterministico maior-pra-menor, respeitando pares
  // disponiveis (plano §5.3, caso 1) -- nunca assume estoque infinito.
  function computePlates(totalKg, barKg, pairs) {
    if (!isFinite(totalKg) || !isFinite(barKg)) { return { status: 'invalid' }; }
    if (totalKg < barKg - 0.01) { return { status: 'below_bar' }; }
    if (Math.abs(totalKg - barKg) < 0.01) { return { status: 'bar_only' }; }

    var perSide = Math.round(((totalKg - barKg) / 2) * 100) / 100;
    var remaining = perSide;
    var used = {};
    var sizes = Object.keys(pairs).map(Number).sort(function (a, b) { return b - a; });
    for (var i = 0; i < sizes.length; i++) {
      var size = sizes[i];
      var available = pairs[size] || 0;
      var count = 0;
      while (remaining >= size - 0.01 && count < available) {
        remaining = Math.round((remaining - size) * 100) / 100;
        count++;
      }
      if (count > 0) { used[size] = count; }
    }
    if (remaining > 0.01) { return { status: 'impossible' }; }
    return { status: 'ok', used: used, perSide: perSide };
  }

  // Caso 4 do plano: quando o alvo e' impossivel com o estoque, procura o
  // mais proximo alcancavel pra baixo/cima -- nunca arredonda escondido,
  // so' sugere.
  function findNearestAchievable(totalKg, barKg, pairs, direction) {
    var step = 0.5;
    for (var delta = step; delta <= 40; delta += step) {
      var candidate = Math.round((totalKg + direction * delta) * 100) / 100;
      if (candidate < barKg - 0.01) { break; }
      var result = computePlates(candidate, barKg, pairs);
      if (result.status === 'ok' || result.status === 'bar_only') { return candidate; }
    }
    return null;
  }

  function renderPlateInventoryRows(container, pairs) {
    container.innerHTML = DEFAULT_PLATE_SIZES.map(function (size) {
      var count = pairs[size] != null ? pairs[size] : 0;
      return '<div class="workout-load-input__plate-row">' +
        '<span class="workout-load-input__mini-label">' + fmtNumber(size) + ' kg</span>' +
        '<input type="number" inputmode="numeric" step="1" min="0" class="workout-load-input__reps-field" ' +
          'data-plate-size="' + size + '" value="' + count + '" ' +
          'aria-label="Pares de ' + fmtNumber(size) + ' quilos disponíveis">' +
        '</div>';
    }).join('');
  }

  function wirePlateCalculator(widget) {
    var calc = widget.querySelector('[data-workout-plate-calculator]');
    if (!calc) { return; }
    var weightField = widget.querySelector('[data-workout-load-field]');
    var targetDisplay = calc.querySelector('[data-plate-target-display]');
    var barOptions = calc.querySelector('[data-plate-bar-options]');
    var barOtherToggle = calc.querySelector('[data-plate-bar-other-toggle]');
    var barOtherField = calc.querySelector('[data-plate-bar-other-field]');
    var inventoryContainer = calc.querySelector('[data-plate-inventory]');
    var resultEl = calc.querySelector('[data-plate-result]');
    var checkEl = calc.querySelector('[data-plate-check]');
    var useBtn = calc.querySelector('[data-plate-use-total]');
    if (!weightField || !targetDisplay || !barOptions || !inventoryContainer || !resultEl || !checkEl || !useBtn) { return; }

    var config = loadPlateConfig();
    var target = 0;

    function currentBarKg() {
      var activePill = barOptions.querySelector('.is-selected');
      if (activePill) { return parseFloat(activePill.getAttribute('data-bar-value')); }
      var other = parseFloat((barOtherField.value || '').replace(',', '.'));
      return isFinite(other) && other >= 0 ? other : config.barKg;
    }

    function currentPairs() {
      var pairs = {};
      inventoryContainer.querySelectorAll('[data-plate-size]').forEach(function (input) {
        var size = parseFloat(input.getAttribute('data-plate-size'));
        var count = parseInt(input.value, 10);
        pairs[size] = isFinite(count) && count >= 0 ? count : 0;
      });
      return pairs;
    }

    function persistConfig() {
      config = { barKg: currentBarKg(), pairs: currentPairs() };
      savePlateConfig(config);
    }

    function renderResult(result, barKg, pairs) {
      if (result.status === 'below_bar') {
        resultEl.textContent = 'O total precisa incluir a barra (' + fmtNumber(barKg) + ' kg) — ajuste a barra ou o peso alvo.';
        checkEl.textContent = '';
        useBtn.hidden = true;
        return;
      }
      if (result.status === 'bar_only') {
        resultEl.textContent = 'Somente a barra.';
        checkEl.textContent = '';
        useBtn.hidden = false;
        return;
      }
      if (result.status === 'impossible') {
        var below = findNearestAchievable(target, barKg, pairs, -1);
        var above = findNearestAchievable(target, barKg, pairs, 1);
        var alternatives = [];
        if (below !== null) { alternatives.push(fmtNumber(below) + ' kg'); }
        if (above !== null) { alternatives.push(fmtNumber(above) + ' kg'); }
        resultEl.textContent = 'Não é possível montar ' + fmtNumber(target) + ' kg com o estoque configurado.';
        checkEl.textContent = alternatives.length ? ('Mais próximo: ' + alternatives.join(' ou ') + '.') : 'Ajuste o estoque de anilhas.';
        useBtn.hidden = true;
        return;
      }
      var sizes = Object.keys(result.used).map(Number).sort(function (a, b) { return b - a; });
      var perSideParts = [];
      sizes.forEach(function (size) {
        for (var i = 0; i < result.used[size]; i++) { perSideParts.push(fmtNumber(size)); }
      });
      var totalPlatesKg = sizes.reduce(function (sum, size) { return sum + size * result.used[size] * 2; }, 0);
      resultEl.textContent = 'De cada lado: ' + perSideParts.join(' + ') + ' kg';
      checkEl.textContent = fmtNumber(barKg) + ' kg de barra + 2 × ' + fmtNumber(result.perSide) + ' kg = ' + fmtNumber(barKg + totalPlatesKg) + ' kg';
      useBtn.hidden = false;
    }

    function recompute() {
      targetDisplay.textContent = fmtNumber(target);
      var barKg = currentBarKg();
      var pairs = currentPairs();
      renderResult(computePlates(target, barKg, pairs), barKg, pairs);
    }

    renderPlateInventoryRows(inventoryContainer, config.pairs);
    barOptions.querySelectorAll('[data-bar-value]').forEach(function (pill) {
      if (parseFloat(pill.getAttribute('data-bar-value')) === config.barKg) { pill.classList.add('is-selected'); }
      pill.addEventListener('click', function () {
        barOptions.querySelectorAll('[data-bar-value]').forEach(function (p) { p.classList.remove('is-selected'); });
        pill.classList.add('is-selected');
        barOtherField.value = '';
        barOtherField.hidden = true;
        persistConfig();
        recompute();
      });
    });
    if (barOtherToggle && barOtherField) {
      barOtherToggle.addEventListener('click', function () {
        barOtherField.hidden = !barOtherField.hidden;
        if (!barOtherField.hidden) {
          barOptions.querySelectorAll('[data-bar-value]').forEach(function (p) { p.classList.remove('is-selected'); });
          barOtherField.focus();
        }
      });
      barOtherField.addEventListener('input', function () { persistConfig(); recompute(); });
    }
    inventoryContainer.addEventListener('input', function () { persistConfig(); recompute(); });

    calc.querySelectorAll('[data-plate-target-step]').forEach(function (stepBtn) {
      var delta = parseFloat(stepBtn.getAttribute('data-plate-target-step'));
      stepBtn.addEventListener('click', function () {
        target = Math.max(0, Math.round((target + delta) * 100) / 100);
        recompute();
      });
    });

    useBtn.addEventListener('click', function () {
      // "Usar X kg" aplica ao RASCUNHO (marca dirty, agenda o auto-save
      // de rascunho) -- nunca salva sozinho (plano §5.2: "Nunca salva
      // automaticamente").
      weightField.value = target;
      markDirty(weightField);
      updateSaveLabel(widget);
      scheduleDraftSave(widget);
    });

    calc.addEventListener('toggle', function () {
      if (!calc.open) { return; }
      // "Abrir não altera carga" -- só semeia o alvo da calculadora com o
      // peso atual do rascunho; nada é escrito de volta até "Usar".
      var weightParsed = parseWeightField(weightField);
      target = weightParsed.ok && weightParsed.value !== null ? weightParsed.value : 0;
      recompute();
    });
  }

  // Rascunho em visibilitychange (item 8): campo com valor digitado mas
  // nao salvo entra no outbox mesmo sem o aluno clicar em "Salvar" — cobre
  // o caso comum no celular de trocar de app/apagar a tela no meio do
  // registro.
  function saveDirtyDrafts() {
    document.querySelectorAll('[data-workout-load-input]').forEach(function (widget) {
      var weightField = widget.querySelector('[data-workout-load-field]');
      var repsField = widget.querySelector('[data-workout-reps-field]');
      var weightDirty = weightField && weightField.hasAttribute('data-dirty');
      var repsDirty = repsField && repsField.hasAttribute('data-dirty');
      if (!weightDirty && !repsDirty) { return; }
      // Correção real (plano §3.2): antes, isto gravava direto na outbox
      // CONFIRMADA -- fechar o app no meio da digitação virava um POST de
      // "realizado" sem o aluno nunca ter tocado em Salvar. Agora só
      // grava no store de rascunho; a promoção pra confirmado exige o
      // clique explícito (saveWidget).
      flushPendingDraft(widget);
    });
  }

  // Troca de exercicio (Entrega 4): pills de variacao irma
  // (public_workouts_extras.py::sibling_variations, ja usadas so como
  // referencia na aba Cargas) ganham acao aqui — clicar troca QUAL
  // movimento este widget grava, sem endpoint novo nenhum:
  // record_load ja aceita qualquer movement_slug livremente
  // (public_workouts/services.py), nunca validou contra o payload do dia.
  // buildEntryFromWidget le data-movement-slug do proprio widget em tempo
  // de Salvar, entao so mudar esse atributo aqui basta — zero mudanca no
  // fluxo de outbox/idempotencia acima.
  function wireSubstitutePills(widget) {
    var pillsContainer = widget.querySelector('[data-workout-substitute-pills]');
    if (!pillsContainer) { return; }
    var pills = pillsContainer.querySelectorAll('[data-substitute-slug]');
    var weightField = widget.querySelector('[data-workout-load-field]');
    var repsField = widget.querySelector('[data-workout-reps-field]');
    pills.forEach(function (pill) {
      pill.addEventListener('click', function () {
        if (pill.classList.contains('is-active')) { return; }
        widget.setAttribute('data-movement-slug', pill.getAttribute('data-substitute-slug'));
        pills.forEach(function (p) { p.classList.toggle('is-active', p === pill); });
        // Plano §1.5: nunca carrega peso/reps de um movimento pra outro —
        // 60kg de barra nao significa nada em halteres. Achado real: o
        // comportamento anterior deixava o valor antigo no campo depois
        // da troca, sem nunca limpar.
        if (weightField) { weightField.value = ''; weightField.removeAttribute('data-dirty'); }
        if (repsField) { repsField.value = ''; repsField.removeAttribute('data-dirty'); }
        setRirSelection(widget, null, '');
        setStatus(widget, '', false);
        // BUG REAL corrigido nesta varredura: sem isto, o widget mantinha
        // a data-today-idempotency-key do movimento ANTERIOR -- salvar
        // depois da troca mandaria supersedes_idempotency_key do
        // movimento A junto com o peso do movimento B, e correct_load
        // (que herda movement_slug do ALVO, nunca do payload) corrigiria
        // o registro de A com o peso de B, sem nunca atribuir nada a B.
        // A chave "de hoje" so' e' conhecida pro movimento ORIGINAL deste
        // widget (resolvida no load da pagina) -- depois de trocar, fica
        // desconhecida pra este widget, entao "Salvar" cria um registro
        // novo pro movimento B (nunca corrige o A por engano).
        widget.removeAttribute('data-today-idempotency-key');
        widget.removeAttribute('data-today-top-set-idempotency-key');
        widget.removeAttribute('data-today-warmup-idempotency-key');
        updateSaveLabel(widget);
        // Plano §1.5: so carrega rascunho do DESTINO (nunca o que acabou
        // de ser limpo acima) -- data-movement-slug ja apontou pro novo
        // movimento na linha de cima, entao hydrateDraft busca a chave
        // certa.
        hydrateDraft(widget);
      });
    });
  }

  /* ══ CARD COMPARTILHÁVEL (fundação) ══════════════════════════════
   * Decidido com o Renan em 24/09/2026: por agora so' texto pro Web
   * Share API, imagem gerada fica pra depois. O conteudo (title/text)
   * e' calculado no SERVIDOR (templatetags::share_content_for_chart,
   * mesmo `chart` que ja alimenta o card -- nunca um segundo calculo
   * divergente) e chega aqui so' como atributo pronto pra ler.
   *
   * GANCHO pra versao futura com imagem: quando existir, o servidor
   * passaria a mandar tambem `data-share-image-url` (ou equivalente) --
   * este bloco so' precisaria ler esse atributo extra e trocar
   * `navigator.share({title, text})` por `navigator.share({title, text,
   * files: [...]})` quando presente. Nao muda a estrutura de botao/
   * evento abaixo, so' o payload.
   */

  function announceShareResult(button, message) {
    var status = button.parentElement && button.parentElement.querySelector('[data-workout-share-status]');
    if (!status) { return; }
    status.textContent = message;
  }

  function wireShareButtons() {
    document.querySelectorAll('[data-workout-share]').forEach(function (button) {
      button.addEventListener('click', function () {
        var title = button.getAttribute('data-share-title') || '';
        var text = button.getAttribute('data-share-text') || '';
        if (navigator.share) {
          // Cancelar o painel do sistema (ou a API recusar) nao e' erro
          // de verdade -- silencioso, mesmo padrao do resto do arquivo
          // pra reject que nao muda nada pro aluno.
          navigator.share({ title: title, text: text }).catch(function () {});
          return;
        }
        // Fallback pra navegador sem Web Share API (ex.: desktop Chrome/
        // Firefox mais antigos) -- copia pro clipboard em vez de nao
        // fazer nada.
        var toCopy = title ? (title + '\n' + text) : text;
        if (!navigator.clipboard || !navigator.clipboard.writeText) {
          announceShareResult(button, 'Compartilhamento não é suportado neste navegador.');
          return;
        }
        navigator.clipboard.writeText(toCopy)
          .then(function () { announceShareResult(button, 'Copiado! Cole onde quiser compartilhar.'); })
          .catch(function () { announceShareResult(button, 'Não foi possível copiar automaticamente.'); });
      });
    });
  }

  function wireKeyboardNavBehavior() {
    var numericInputSelector = [
      '[data-workout-load-field]',
      '[data-workout-reps-field]',
      '[data-workout-rir-other-field]',
      '[data-plate-bar-other-field]',
    ].join(',');
    document.addEventListener('focusin', function (event) {
      if (event.target.matches && event.target.matches(numericInputSelector)) {
        document.body.classList.add('workout-keyboard-open');
      }
    });
    document.addEventListener('focusout', function (event) {
      if (!event.target.matches || !event.target.matches(numericInputSelector)) { return; }
      window.setTimeout(function () {
        var active = document.activeElement;
        if (!active || !active.matches || !active.matches(numericInputSelector)) {
          document.body.classList.remove('workout-keyboard-open');
        }
      }, 0);
    });
  }

  function wireWidgets() {
    document.querySelectorAll('[data-workout-load-input]').forEach(function (widget) {
      var field = widget.querySelector('[data-workout-load-field]');
      var repsField = widget.querySelector('[data-workout-reps-field]');
      var saveBtn = widget.querySelector('[data-workout-load-save]');
      if (field) {
        field.addEventListener('input', function () {
          markDirty(field); updateSaveLabel(widget); scheduleDraftSave(widget);
        });
      }
      if (repsField) {
        repsField.addEventListener('input', function () {
          markDirty(repsField); updateSaveLabel(widget); scheduleDraftSave(widget);
        });
      }
      var warmupToggle = widget.querySelector('[data-workout-load-warmup-toggle]');
      if (warmupToggle) {
        warmupToggle.addEventListener('change', function () {
          syncCorrectionTargetForRole(widget);
        });
      }
      if (saveBtn) { saveBtn.addEventListener('click', function () { saveWidget(widget); }); }
      widget.querySelectorAll('[data-workout-load-step]').forEach(function (stepBtn) {
        var delta = parseFloat(stepBtn.getAttribute('data-workout-load-step'));
        stepBtn.addEventListener('click', function () {
          stepField(field, delta); updateSaveLabel(widget); scheduleDraftSave(widget);
        });
      });
      widget.querySelectorAll('[data-workout-reps-step]').forEach(function (stepBtn) {
        var delta = parseInt(stepBtn.getAttribute('data-workout-reps-step'), 10);
        stepBtn.addEventListener('click', function () {
          stepReps(repsField, delta); updateSaveLabel(widget); scheduleDraftSave(widget);
        });
      });
      wireEffortDisclosure(widget);
      wirePlateCalculator(widget);
      wireSubstitutePills(widget);
      updateSaveLabel(widget);
      // Rascunho local prevalece sobre o eco "confirmado hoje" que o
      // servidor ja pre-preencheu (ver docstring de hydrateDraft).
      hydrateDraft(widget);
    });
  }

  /* ══ BOOT ═══════════════════════════════════════════════════════ */

  function init() {
    if (!planSlug()) { return; }
    wireWidgets();
    wireShareButtons();
    wireKeyboardNavBehavior();
    drainOutbox();
    fetchLastLoadByMovement().then(paintHints);
    document.addEventListener('visibilitychange', function () {
      if (document.visibilityState === 'hidden') { saveDirtyDrafts(); }
    });
    window.addEventListener('online', drainOutbox);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Exportado pro hook de logout que ainda nao existe (ver docstring) e
  // pra inspecao/teste manual sem reescrever a fila.
  window.PublicWorkoutLoadTracker = {
    drainOutbox: drainOutbox,
    clearOutbox: clearOutbox,
    clearDrafts: clearDrafts,
    listEntries: listEntries,
  };
})();
