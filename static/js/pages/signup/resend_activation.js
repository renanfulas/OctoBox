/*
ARQUIVO: reenvio self-service do email de ativacao na tela de sucesso do checkout.

POR QUE ELE EXISTE:
- Achado S4 do relatorio de simulacao de 30 dias: quando o email de ativacao
  falha, o cliente que ja pagou nao tinha NENHUM caminho na tela — so um
  "em instantes voce vai receber um email" que nunca mudava.
*/
(function () {
  var panel = document.querySelector('[data-resend-activation]');
  if (!panel) return;

  var button = panel.querySelector('[data-resend-button]');
  var status = panel.querySelector('[data-resend-status]');
  var url = panel.dataset.resendUrl;

  function getCsrf() {
    var el = panel.querySelector('[name=csrfmiddlewaretoken]');
    return el ? el.value : '';
  }

  function showStatus(message, tone) {
    if (!status) return;
    status.hidden = false;
    status.textContent = message;
    status.className = 'checkout-resend-status checkout-resend-status--' + (tone || 'info');
  }

  if (!button) return;

  button.addEventListener('click', function () {
    if (button.disabled) return;
    button.disabled = true;
    var originalText = button.textContent;
    button.textContent = 'Enviando...';
    showStatus('Enviando...', 'info');

    var body = new URLSearchParams({ csrfmiddlewaretoken: getCsrf() });

    fetch(url, { method: 'POST', body: body, headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (response) {
        return response.json().catch(function () { return {}; }).then(function (data) {
          return { ok: response.ok, data: data };
        });
      })
      .then(function (result) {
        if (result.ok && result.data.ok) {
          showStatus(result.data.message || 'E-mail reenviado.', 'success');
          button.textContent = 'Reenviado!';
          // O servidor tem cooldown de 45s pro mesmo cadastro — reabilita o
          // botao depois desse tempo em vez de exigir recarregar a pagina.
          setTimeout(function () {
            button.disabled = false;
            button.textContent = originalText;
          }, 45000);
          return;
        }
        showStatus(
          (result.data && result.data.error) || 'Não foi possível reenviar agora. Tente de novo em instantes.',
          'error'
        );
        button.disabled = false;
        button.textContent = originalText;
      })
      .catch(function () {
        showStatus('Falha de conexão. Verifique sua internet e tente de novo.', 'error');
        button.disabled = false;
        button.textContent = originalText;
      });
  });
})();
