/*
ARQUIVO: indicador vivo de requisito de senha na criacao da conta do Owner.

POR QUE ELE EXISTE:
- Onda 6 (docs/plans/student-login-magic-link-bugs-corda.md): o campo de senha exigia um
  minimo de caracteres mas nao mostrava ao vivo quantos caracteres faltavam nem se a senha
  batia o padrao — a unica pista era o placeholder, que some assim que a pessoa digita.

PONTOS CRITICOS:
- So mostra o que o backend de fato valida (tamanho minimo, nao ser so numeros) — nao
  promete regra que signup/forms.py::OnboardingForm nao aplica (ex.: nao exige letra E
  numero, isso nao existe nos AUTH_PASSWORD_VALIDATORS padrao do Django).
- NUNCA transmite nem loga o valor da senha: tudo roda em memoria, lendo o `.value` do
  proprio input, sem fetch/XHR nenhum.
*/
(function () {
  var container = document.querySelector('[data-password-hints]');
  if (!container) return;

  var field = container.closest('.checkout-field');
  var input = field ? field.querySelector('input') : null;
  if (!input) return;

  var minLength = parseInt(container.dataset.minLength, 10) || 10;
  var lengthHint = container.querySelector('[data-hint="length"]');
  var lengthCount = container.querySelector('[data-hint-count]');
  var numericHint = container.querySelector('[data-hint="not-numeric"]');

  function setHintState(hintEl, met) {
    if (!hintEl) return;
    hintEl.classList.toggle('is-met', met);
    var icon = hintEl.querySelector('.checkout-password-hint-icon');
    if (icon) icon.textContent = met ? '●' : '○';
  }

  function update() {
    var value = input.value || '';
    if (lengthCount) lengthCount.textContent = String(Math.min(value.length, minLength));
    setHintState(lengthHint, value.length >= minLength);
    setHintState(numericHint, value.length > 0 && !/^[0-9]+$/.test(value));
  }

  input.addEventListener('input', update);
  update();
})();
