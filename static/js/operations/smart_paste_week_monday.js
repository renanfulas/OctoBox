/*
ARQUIVO: snap automático de data para segunda-feira em campos Smart Paste.

POR QUE ELE EXISTE:
- planos semanais de WOD sempre começam na segunda-feira; permitir outras
  datas causa conflito de indexação no WeeklyWodPlan.

O QUE FAZ:
1. intercepta change/blur no campo dd/mm e no picker nativo.
2. se o dia selecionado não for segunda (weekday=1), recua para a segunda
   da mesma semana e mostra hint "ajustado para segunda dd/mm".
3. atualiza ambos os campos (texto + picker) de forma coerente.
4. gerencia o botão de abrir calendário — usa o picker REAL (não clone)
   posicionado perto do botão para o calendário nativo abrir ali.

POR QUE SÓ ESTE ARQUIVO GERENCIA O BOTÃO:
- wod_smart_paste.js ignora o botão quando o campo está num monday-wrap
  para evitar duplo disparo e conflito entre as duas openTransientPicker.
*/

(function () {
  'use strict';

  function pad(v) {
    return String(v).padStart(2, '0');
  }

  function prevMonday(date) {
    var d = new Date(date);
    var day = d.getDay(); // 0=dom, 1=seg, ..., 6=sab
    var diff = day === 0 ? -6 : 1 - day;
    d.setDate(d.getDate() + diff);
    return d;
  }

  function formatDDMM(date) {
    return pad(date.getDate()) + '/' + pad(date.getMonth() + 1);
  }

  function formatYMD(date) {
    return (
      date.getFullYear() + '-' + pad(date.getMonth() + 1) + '-' + pad(date.getDate())
    );
  }

  function parsePickerDate(ymdString) {
    if (!ymdString) return null;
    var parts = ymdString.split('-');
    if (parts.length !== 3) return null;
    var d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
    return isNaN(d.getTime()) ? null : d;
  }

  function parseTextDate(ddmm) {
    var normalized = String(ddmm || '').replace(/\D/g, '');
    if (normalized.length < 4) return null;
    var day = Number(normalized.slice(0, 2));
    var month = Number(normalized.slice(2, 4));
    var today = new Date();
    var year = today.getFullYear();
    var d = new Date(year, month - 1, day);
    if (isNaN(d.getTime())) return null;
    if (d < new Date(today.getFullYear(), today.getMonth(), today.getDate())) {
      d = new Date(year + 1, month - 1, day);
    }
    return isNaN(d.getTime()) ? null : d;
  }

  function applySnap(wrap) {
    var textField = wrap.querySelector('[data-smart-date-input]');
    var picker = wrap.querySelector('input[type="date"]');
    var hint = wrap.querySelector('[data-smart-date-monday-hint]');
    var button = wrap.querySelector('[data-smart-date-button]');
    if (!textField || !picker) return;

    // ── Abre o calendário nativo ──────────────────────────────────────────────
    // Usa o picker REAL (não um clone) para manter o trusted-gesture context.
    // Posiciona o picker perto do botão para que o calendário abra ali.
    // Limpa clip/clip-path da classe .smart-paste-native-picker para que
    // o browser considere o elemento como renderizado ao chamar showPicker().
    // void picker.offsetHeight força reflow síncrono antes de showPicker(),
    // garantindo que a posição já está computada no primeiro clique.
    function openTransientPicker() {
      var anchor = button || textField;
      var rect = anchor ? anchor.getBoundingClientRect() : null;

      var hadHidden = picker.hasAttribute('hidden');
      var savedCssText = picker.style.cssText || '';

      picker.style.cssText = [
        'position:fixed',
        rect ? 'left:' + Math.round(rect.left) + 'px' : 'left:0',
        rect ? 'top:' + Math.round(rect.bottom + 4) + 'px' : 'top:0',
        'width:1px',
        'height:1px',
        'opacity:0',
        'pointer-events:none',
        'z-index:9999',
        'clip:auto',
        'clip-path:none',
        'overflow:visible',
        'white-space:normal',
        'margin:0',
        'padding:0',
        'border:0'
      ].join(';');

      if (hadHidden) picker.removeAttribute('hidden');
      picker.removeAttribute('aria-hidden');

      // Força reflow síncrono: garante que o browser registrou a nova posição
      // antes de showPicker() — sem isso o primeiro clique abre no topo da tela.
      void picker.offsetHeight;

      function restore() {
        picker.style.cssText = savedCssText;
        if (hadHidden) picker.setAttribute('hidden', '');
        picker.setAttribute('aria-hidden', 'true');
      }

      picker.addEventListener('change', restore, { once: true });
      picker.addEventListener('blur', function () {
        window.setTimeout(restore, 50);
      }, { once: true });

      if (typeof picker.showPicker === 'function') {
        try {
          picker.showPicker();
        } catch (e) {
          picker.click();
          picker.focus();
        }
      } else {
        picker.click();
        picker.focus();
      }
    }

    // ── Snap para segunda ────────────────────────────────────────────────────
    function snapAndUpdate(date) {
      if (!date) return;
      var monday = prevMonday(date);
      var isAlreadyMonday = date.getDay() === 1;

      textField.value = formatDDMM(monday);
      picker.value = formatYMD(monday);

      if (hint) {
        if (!isAlreadyMonday) {
          hint.textContent = 'Ajustado para segunda ' + formatDDMM(monday);
          hint.hidden = false;
        } else {
          hint.hidden = true;
        }
      }

      textField.dispatchEvent(new Event('input', { bubbles: true }));
    }

    picker.addEventListener('change', function () {
      snapAndUpdate(parsePickerDate(picker.value));
    });

    textField.addEventListener('blur', function () {
      snapAndUpdate(parseTextDate(textField.value));
    });

    if (button) {
      button.addEventListener('click', function () {
        openTransientPicker();
      });
    }
  }

  document.querySelectorAll('[data-smart-date-monday-wrap]').forEach(applySnap);
})();
