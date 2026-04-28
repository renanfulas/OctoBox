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
    if (!textField || !picker) return;

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

    var button = wrap.querySelector('[data-smart-date-button]');
    if (button) {
      button.addEventListener('click', function () {
        if (typeof picker.showPicker === 'function') {
          picker.showPicker();
        } else {
          picker.click();
          picker.focus();
        }
      });
    }
  }

  document.querySelectorAll('[data-smart-date-monday-wrap]').forEach(applySnap);
})();
