(function () {
  'use strict';

  function numberValue(value) {
    var normalized = String(value || '').replace(',', '.');
    var parsed = Number(normalized);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function field(label, value, type, key) {
    var wrapper = document.createElement('label');
    wrapper.textContent = label;
    var input = document.createElement(type === 'textarea' ? 'textarea' : 'input');
    if (type !== 'textarea') input.type = type || 'text';
    input.value = value == null ? '' : value;
    input.dataset.key = key;
    if (type === 'number') { input.min = '0'; input.step = '0.1'; input.inputMode = 'decimal'; }
    wrapper.appendChild(input);
    return wrapper;
  }

  function button(label, action, danger) {
    var el = document.createElement('button');
    el.type = 'button'; el.className = danger ? 'button nutrition-editor__danger' : 'button';
    el.textContent = label; el.dataset.action = action;
    return el;
  }

  function normalize(payload) {
    payload = payload && typeof payload === 'object' ? payload : {};
    payload.schema_version = 1;
    payload.daily_targets = payload.daily_targets || {};
    payload.meals = Array.isArray(payload.meals) ? payload.meals : [];
    return payload;
  }

  function init(root) {
    var hidden = document.getElementById(root.dataset.inputId);
    if (!hidden) return;
    var model;
    try { model = normalize(JSON.parse(hidden.value || '{}')); } catch (_) { model = normalize({}); }
    var targetsRoot = root.querySelector('[data-nutrition-targets]');
    var mealsRoot = root.querySelector('[data-nutrition-meals]');
    var preview = root.querySelector('[data-nutrition-preview]');

    function sync() {
      hidden.value = JSON.stringify(model);
      preview.textContent = JSON.stringify(model, null, 2);
    }

    function renderTargets() {
      targetsRoot.innerHTML = '<h3>Metas diárias</h3>';
      var grid = document.createElement('div'); grid.className = 'nutrition-editor__grid';
      [['Calorias','kcal'],['Proteína (g)','protein_g'],['Carboidratos (g)','carbs_g'],['Gorduras (g)','fat_g']].forEach(function (entry) {
        var control = field(entry[0], model.daily_targets[entry[1]], 'number', entry[1]);
        control.querySelector('input').addEventListener('input', function (event) {
          model.daily_targets[event.target.dataset.key] = numberValue(event.target.value); sync();
        });
        grid.appendChild(control);
      });
      targetsRoot.appendChild(grid);
    }

    function renderMeals() {
      mealsRoot.innerHTML = '';
      model.meals.forEach(function (meal, mealIndex) {
        meal.items = Array.isArray(meal.items) ? meal.items : [];
        meal.substitutes = Array.isArray(meal.substitutes) ? meal.substitutes : [];
        var card = document.createElement('section'); card.className = 'nutrition-editor__meal';
        var head = document.createElement('div'); head.className = 'nutrition-editor__meal-head';
        [['Nome da refeição', 'label'], ['Horário', 'time']].forEach(function (entry) {
          var control = field(entry[0], meal[entry[1]], 'text', entry[1]);
          control.querySelector('input').addEventListener('input', function (event) {
            meal[event.target.dataset.key] = event.target.value;
            meal.meal_id = meal.meal_id || ('refeicao-' + (mealIndex + 1)); sync();
          }); head.appendChild(control);
        });
        var removeMeal = button('Remover refeição', 'remove-meal', true);
        removeMeal.addEventListener('click', function () { model.meals.splice(mealIndex, 1); renderMeals(); sync(); });
        head.appendChild(removeMeal); card.appendChild(head);

        var itemsTitle = document.createElement('h4'); itemsTitle.textContent = 'Alimentos'; card.appendChild(itemsTitle);
        meal.items.forEach(function (item, itemIndex) {
          var row = document.createElement('div'); row.className = 'nutrition-editor__item';
          [['Alimento','food','text'],['Quantidade','quantity','text'],['kcal','kcal','number'],['Proteína','protein_g','number'],['Carbo','carbs_g','number'],['Gordura','fat_g','number']].forEach(function (entry) {
            var control = field(entry[0], item[entry[1]], entry[2], entry[1]);
            control.querySelector('input').addEventListener('input', function (event) {
              item[event.target.dataset.key] = entry[2] === 'number' ? numberValue(event.target.value) : event.target.value; sync();
            }); row.appendChild(control);
          });
          var remove = button('×', 'remove-item', true); remove.addEventListener('click', function () { meal.items.splice(itemIndex, 1); renderMeals(); sync(); }); row.appendChild(remove); card.appendChild(row);
        });
        var addItem = button('+ Alimento', 'add-item'); addItem.addEventListener('click', function () { meal.items.push({food:'',quantity:''}); renderMeals(); sync(); }); card.appendChild(addItem);

        var subsTitle = document.createElement('h4'); subsTitle.textContent = 'Substituições'; card.appendChild(subsTitle);
        meal.substitutes.forEach(function (substitute, subIndex) {
          var row = document.createElement('div'); row.className = 'nutrition-editor__substitute';
          [['Alimento','food'],['Quantidade','quantity']].forEach(function (entry) {
            var control = field(entry[0], substitute[entry[1]], 'text', entry[1]);
            control.querySelector('input').addEventListener('input', function (event) { substitute[event.target.dataset.key] = event.target.value; sync(); }); row.appendChild(control);
          });
          var remove = button('×', 'remove-substitute', true); remove.addEventListener('click', function () { meal.substitutes.splice(subIndex, 1); renderMeals(); sync(); }); row.appendChild(remove); card.appendChild(row);
        });
        var addSub = button('+ Substituição', 'add-substitute'); addSub.addEventListener('click', function () { meal.substitutes.push({food:'',quantity:''}); renderMeals(); sync(); }); card.appendChild(addSub);
        var note = field('Observações da refeição', meal.note || '', 'textarea', 'note');
        note.querySelector('textarea').addEventListener('input', function (event) { meal.note = event.target.value; sync(); }); card.appendChild(note);
        mealsRoot.appendChild(card);
      });
    }

    root.querySelector('[data-add-meal]').addEventListener('click', function () {
      var index = model.meals.length + 1;
      model.meals.push({meal_id:'refeicao-' + index,label:'',time:'',items:[{food:'',quantity:''}],substitutes:[],note:''});
      renderMeals(); sync();
    });
    renderTargets(); renderMeals(); sync();
  }

  function boot() { document.querySelectorAll('[data-nutrition-editor]').forEach(init); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
