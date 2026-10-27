/* Rascunho textual recuperável. Nunca envia texto ao aplicador/publicador de WOD. */
(function () {
  'use strict';

  function uuid() {
    if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
    var bytes = new Uint8Array(16);
    window.crypto.getRandomValues(bytes);
    bytes[6] = (bytes[6] & 15) | 64;
    bytes[8] = (bytes[8] & 63) | 128;
    var hex = Array.from(bytes, function (byte) { return byte.toString(16).padStart(2, '0'); }).join('');
    return hex.slice(0, 8) + '-' + hex.slice(8, 12) + '-' + hex.slice(12, 16) + '-' + hex.slice(16, 20) + '-' + hex.slice(20);
  }

  function weeklyDate(value) {
    var match = String(value || '').match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
    if (!match) return '';
    var year = Number(match[3]), month = Number(match[2]), day = Number(match[1]);
    var date = new Date(Date.UTC(year, month - 1, day));
    if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day || date.getUTCDay() !== 1) return '';
    return match[3] + '-' + match[2] + '-' + match[1];
  }

  document.querySelectorAll('[data-wod-input-draft]').forEach(function (form) {
    var field = form.querySelector('[data-wod-draft-source]');
    var status = form.querySelector('[data-wod-draft-status]');
    var recover = form.querySelector('[data-wod-draft-recover]');
    var discard = form.querySelector('[data-wod-draft-discard]');
    var url = form.dataset.draftUrl;
    if (!field || !status || !url) return;
    var active = null;
    var timer = null;
    var epoch = 0;

    function setStatus(message) { status.textContent = message; }
    function sourceLength(value) { return Array.from(value).length; }
    function scopeFromForm() {
      if (form.dataset.draftKind === 'daily') {
        return { scope_kind: 'daily', session_id: form.dataset.sessionId };
      }
      var week = weeklyDate((form.querySelector('[name=week_start]') || {}).value);
      var program = (form.querySelector('[name=workout_program]') || {}).value;
      if (!week || !program) return null;
      var data = { scope_kind: 'weekly', week_start: week, workout_program_id: program };
      var planId = (form.querySelector('[name=plan_id]') || {}).value;
      // Um plan_id da semana anterior não é autoridade para o novo escopo.
      if (planId && form.dataset.initialWeek === week && form.dataset.initialProgram === program) data.plan_id = planId;
      return data;
    }
    function key(scope) { return scope ? JSON.stringify(scope) : ''; }
    function request(method, data) {
      var options = { method: method, credentials: 'same-origin', headers: { 'Accept': 'application/json' } };
      if (method === 'POST') {
        options.headers['Content-Type'] = 'application/json';
        options.headers['X-CSRFToken'] = (form.querySelector('[name=csrfmiddlewaretoken]') || {}).value || '';
        options.body = JSON.stringify(data);
      }
      var target = method === 'GET' ? url + '?' + new URLSearchParams(data) : url;
      return fetch(target, options).then(function (response) {
        var kind = response.headers.get('content-type') || '';
        if (!kind.includes('application/json')) throw new Error('Sessão expirada. Entre novamente.');
        return response.json().then(function (body) { return { status: response.status, body: body }; });
      });
    }
    function showRecovery(state) {
      if (!state || !state.remote || !recover) return;
      recover.hidden = false;
      setStatus(state.conflict
        ? 'Outra aba alterou o rascunho. Copie seu texto antes de recuperar a versão salva.'
        : 'Há texto salvo no servidor para este contexto. Confira antes de recuperar.');
    }
    function flush(state) {
      if (!state || !state.dirty || state.conflict) return;
      if (state.loading) { state.pending = true; return; }
      if (state.inFlight) { state.pending = true; return; }
      if (sourceLength(state.text) > 20000) {
        if (state === active) setStatus('O limite é 20.000 caracteres; este texto ainda não foi salvo.');
        return;
      }
      var sentText = state.text;
      var sentId = state.retryId || uuid();
      state.retryId = sentId;
      state.inFlight = true;
      if (state === active) setStatus('Salvando rascunho…');
      request('POST', Object.assign({}, state.scope, {
        action: 'save', source_text: sentText, request_id: sentId,
        draft_id: state.id, expected_version: state.version,
      })).then(function (result) {
        var data = result.body;
        if (result.status === 409) {
          state.conflict = true;
          state.remote = null;
          if (state === active) {
            if (recover) recover.hidden = true;
            setStatus('Outra aba alterou o rascunho. Seu texto continua aqui; copie-o antes de recuperar a versão salva.');
            // Manter a operação em voo até obter uma revisão válida. O GET
            // também pode falhar ou informar descarte feito pela outra aba.
            return request('GET', state.scope).then(function (fresh) {
              if (state !== active) return;
              if (fresh.status !== 200 || !fresh.body.ok) throw new Error('draft-refresh-failed');
              if (!fresh.body.draft) {
                setStatus('O rascunho não está mais disponível. Copie seu texto e recarregue a página.');
                return;
              }
              state.remote = fresh.body.draft;
              showRecovery(state);
            }).catch(function () {
              if (state === active) setStatus('Não foi possível recuperar a versão atual. Copie seu texto e recarregue a página.');
            });
          }
          return;
        }
        if (result.status !== 200 || !data.ok) {
          throw new Error(data.reason || (result.status === 429 ? 'Limite de salvamentos. Aguarde e tente novamente.' : 'Não foi possível salvar.'));
        }
        state.id = data.draft.draft_id;
        state.version = data.draft.version;
        // O salvamento substituiu a revisão oferecida pela leitura inicial.
        // Não permitir que Recuperar reintroduza texto e CAS antigos.
        state.remote = null;
        if (state === active && recover) recover.hidden = true;
        if (state === active && discard) discard.hidden = false;
        state.retryId = null;
        state.dirty = state.text !== sentText;
        if (state === active) setStatus(state.dirty ? 'Salvando nova edição…' : 'Rascunho salvo no servidor.');
      }).catch(function (error) {
        if (state === active) setStatus(error.message + ' O texto permanece neste campo.');
      }).finally(function () {
        state.inFlight = false;
        if (state.pending || (state.dirty && !state.retryId && !state.conflict)) {
          state.pending = false;
          flush(state);
        }
      });
    }
    function loadScope(scope, clearField) {
      epoch += 1;
      var ownEpoch = epoch;
      active = scope ? { scope: scope, text: clearField ? '' : field.value, dirty: false,
        id: null, version: null, remote: null, conflict: false, loading: true,
        inFlight: false, pending: false, retryId: null } : null;
      var state = active;
      if (clearField) field.value = '';
      if (recover) recover.hidden = true;
      if (discard) discard.hidden = true;
      if (!scope) { setStatus('Escolha uma segunda-feira e um programa para salvar.'); return; }
      setStatus('Procurando rascunho salvo…');
      request('GET', scope).then(function (result) {
        if (result.status !== 200 || !result.body.ok) throw new Error(result.body.reason || 'Não foi possível recuperar o rascunho.');
        var draft = result.body.draft;
        if (!draft) {
          state.loading = false;
          if (ownEpoch === epoch && !state.text) setStatus('Edite o texto para iniciar um rascunho recuperável.');
          if (state.text && !state.conflict) state.dirty = true;
          if (state.pending) { state.pending = false; flush(state); }
          else if (state.dirty) flush(state);
          return;
        }
        state.id = draft.draft_id;
        state.version = draft.version;
        state.remote = draft;
        if (ownEpoch === epoch && discard) discard.hidden = false;
        // Campo vazio pode ser uma edição deliberada durante o GET.
        if (ownEpoch === epoch && !field.value && !state.dirty) {
          field.value = draft.source_text;
          state.text = draft.source_text;
          setStatus('Rascunho recuperado do servidor.');
        } else if (ownEpoch === epoch && field.value !== draft.source_text) {
          showRecovery(state);
        } else if (ownEpoch === epoch) {
          setStatus('Rascunho recuperável salvo no servidor.');
        }
        state.loading = false;
        if (state.pending) { state.pending = false; flush(state); }
      }).catch(function (error) {
        state.loading = false;
        if (ownEpoch === epoch) {
          setStatus(error.message + ' O texto deste campo permanece disponível.');
        }
        if (state.pending) { state.pending = false; flush(state); }
      });
    }
    function switchScope() {
      var next = scopeFromForm();
      if (key(next) === key(active && active.scope)) return;
      clearTimeout(timer);
      if (active) { active.text = field.value; flush(active); }
      // A troca de escopo muda a chave do rascunho, mas não pode apagar texto
      // que o usuário ainda não salvou. O novo GET decide entre salvar local
      // (se ainda não houver rascunho) ou oferecer recuperação sem sobrescrever.
      loadScope(next, false);
    }

    field.addEventListener('input', function () {
      if (!active) return;
      active.text = field.value;
      active.dirty = true;
      active.retryId = null;
      clearTimeout(timer);
      timer = setTimeout(function () { flush(active); }, 800);
      setStatus('Alterações ainda não salvas.');
    });
    field.addEventListener('blur', function () { clearTimeout(timer); flush(active); });
    if (recover) recover.addEventListener('click', function () {
      if (!active || !active.remote || active.inFlight) return;
      clearTimeout(timer);
      field.value = active.remote.source_text;
      active.text = field.value;
      // A recuperação aceita também a revisão remota usada no próximo CAS.
      active.id = active.remote.draft_id;
      active.version = active.remote.version;
      active.dirty = false;
      active.conflict = false;
      active.retryId = null;
      recover.hidden = true;
      setStatus('Versão salva recuperada.');
      field.focus();
    });
    if (discard) discard.addEventListener('click', function () {
      if (!active || !active.id || active.inFlight) return;
      if (!window.confirm('Descartar o texto salvo deste contexto?')) return;
      clearTimeout(timer);
      var state = active;
      var discardedText = state.text;
      var discarded = false;
      // Serializar descarte e autosave; digitação durante a resposta pertence
      // ao próximo rascunho e não pode ser apagada pelo ACK do anterior.
      state.inFlight = true;
      request('POST', Object.assign({}, state.scope, {
        action: 'discard', draft_id: state.id, expected_version: state.version,
      })).then(function (result) {
        if (result.status !== 200 || !result.body.ok) throw new Error('O rascunho mudou. Recarregue a página antes de descartar.');
        state.id = null;
        state.version = null;
        state.remote = null;
        state.dirty = state.text !== discardedText;
        if (!state.dirty) state.text = '';
        state.conflict = false;
        state.retryId = null;
        discarded = true;
        if (state === active) {
          field.value = state.text;
          discard.hidden = true;
          if (recover) recover.hidden = true;
          setStatus(state.dirty ? 'Rascunho anterior descartado. Salvando nova edição…' : 'Rascunho descartado.');
        }
      }).catch(function (error) {
        if (state === active) setStatus(error.message);
      }).finally(function () {
        state.inFlight = false;
        state.pending = false;
        if (discarded && state.dirty) {
          if (state === active) clearTimeout(timer);
          flush(state);
        }
      });
    });
    if (form.dataset.draftKind === 'weekly') {
      ['week_start', 'workout_program'].forEach(function (name) {
        var control = form.querySelector('[name=' + name + ']');
        if (control) control.addEventListener('change', switchScope);
      });
    }
    form.addEventListener('submit', function () { clearTimeout(timer); flush(active); });
    loadScope(scopeFromForm(), false);
  });
})();
