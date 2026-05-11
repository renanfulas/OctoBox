"""
ARQUIVO: templates do email de onboarding Early Adopter.

POR QUE ELE EXISTE:
- Concentra subject/body do email transacional pos-pagamento.
- Mantem o tom de voz da marca (acolhedor, premium, direto).
- Permite trocar prosa sem precisar mexer em service layer.

O QUE ESTE ARQUIVO FAZ:
1. Gera o subject do email com nome do box.
2. Gera o body em texto plano (multi-paragrafo) com URL de ativacao.

PONTOS CRITICOS:
- Texto plano apenas — gateway (SMTP/Resend) atual nao envia HTML.
- Nao incluir credenciais ou senhas no email (a senha e criada pelo cliente no link).
- Sem caracteres acentuados no subject pra evitar problema de encoding em alguns clientes.
"""
from __future__ import annotations


def build_owner_onboarding_subject(box_name: str) -> str:
    """Subject sem acentos pra maximizar compatibilidade com clientes legacy."""
    safe_box = box_name.strip() or 'seu box'
    return f'OctoBox · Ative sua conta e configure {safe_box}'


def build_owner_onboarding_body(
    *,
    full_name: str,
    box_name: str,
    plan_label: str,
    activation_url: str,
    expires_in_days: int = 7,
) -> str:
    """Corpo do email plain-text. Linhas curtas para boa leitura em mobile."""
    return (
        f'Bem-vindo ao OctoBox, {full_name}!\n'
        '\n'
        f'Recebemos seu pagamento do plano {plan_label} para o {box_name}.\n'
        '\n'
        'Para ativar sua conta e começar a configurar o sistema, clique no link abaixo:\n'
        '\n'
        f'{activation_url}\n'
        '\n'
        f'O link expira em {expires_in_days} dias.\n'
        '\n'
        'Em até 12 horas vamos te chamar no WhatsApp para acompanhar o setup juntos.\n'
        '\n'
        'Bem-vindo entre os 20 primeiros.\n'
        '\n'
        '— Time OctoBox\n'
        'octobox@octoboxfit.com.br\n'
    )


def build_owner_onboarding_html_body(
    *,
    full_name: str,
    box_name: str,
    plan_label: str,
    activation_url: str,
    expires_in_days: int = 7,
) -> str:
    """Versao HTML do email. Compativel com Outlook/Gmail/Apple Mail.

    Estrutura table-based (anti-Outlook) com inline styles. Cores claras +
    accent cyan da marca. Responsivo via media query (Apple Mail/iOS) e fallback
    full-width no mobile via 100% width.
    """
    safe_full_name = _html_escape(full_name)
    safe_box = _html_escape(box_name)
    safe_plan = _html_escape(plan_label)
    safe_url = _html_escape(activation_url)
    return f"""\
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="x-apple-disable-message-reformatting">
<title>Ative sua conta OctoBox</title>
<style>
  @media (max-width: 620px) {{
    .container {{ width: 100% !important; padding: 24px 16px !important; }}
    .card {{ padding: 28px 22px !important; }}
    .h1 {{ font-size: 26px !important; line-height: 1.15 !important; }}
    .cta {{ font-size: 16px !important; padding: 14px 22px !important; }}
  }}
</style>
</head>
<body style="margin:0;padding:0;background:#f4f5f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;color:#0d1320;-webkit-font-smoothing:antialiased;">
  <span style="display:none !important;visibility:hidden;mso-hide:all;font-size:1px;color:#f4f5f7;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;">
    Bem-vindo entre os 20 primeiros. Ative sua conta no link a seguir.
  </span>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f4f5f7;">
    <tr>
      <td align="center" style="padding:40px 16px;">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" class="container" style="width:600px;max-width:100%;">

          <!-- LOGO -->
          <tr>
            <td align="left" style="padding:0 8px 24px;">
              <span style="display:inline-block;font-weight:800;font-size:20px;letter-spacing:-0.04em;color:#0d1320;">
                OctoBox
              </span>
              <span style="display:inline-block;margin-left:6px;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:#60738f;">
                FIT
              </span>
            </td>
          </tr>

          <!-- HERO CARD -->
          <tr>
            <td class="card" style="background:#ffffff;border-radius:20px;padding:44px 40px;box-shadow:0 24px 60px rgba(15,23,42,0.06);border:1px solid rgba(13,19,32,0.06);">

              <!-- EYEBROW -->
              <p style="margin:0 0 16px;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:#ff3eb5;font-weight:800;">
                ✦ Pagamento confirmado
              </p>

              <!-- HEADLINE -->
              <h1 class="h1" style="margin:0 0 18px;font-size:32px;line-height:1.08;letter-spacing:-0.04em;font-weight:800;color:#0d1320;">
                Bem-vindo, {safe_full_name}.
              </h1>

              <!-- BODY -->
              <p style="margin:0 0 28px;font-size:16px;line-height:1.6;color:#3a5371;">
                Recebemos seu pagamento do plano <strong style="color:#0d1320;">{safe_plan}</strong>
                para o <strong style="color:#0d1320;">{safe_box}</strong>.
                Falta um passo simples: criar seu acesso.
              </p>

              <!-- CTA -->
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 28px;">
                <tr>
                  <td bgcolor="#4d8dff" style="border-radius:14px;background:linear-gradient(135deg,#4d8dff,#7cb8ff);">
                    <a href="{safe_url}" class="cta" style="display:inline-block;padding:16px 28px;font-size:16px;font-weight:700;letter-spacing:-0.01em;color:#ffffff;text-decoration:none;border-radius:14px;">
                      Ativar minha conta →
                    </a>
                  </td>
                </tr>
              </table>

              <!-- INFO -->
              <p style="margin:0 0 8px;font-size:13px;line-height:1.5;color:#60738f;">
                O link expira em {expires_in_days} dias. Se preferir, copie e cole no navegador:
              </p>
              <p style="margin:0 0 28px;font-size:12px;line-height:1.5;color:#3a5371;word-break:break-all;font-family:'SF Mono','Menlo','Consolas',monospace;background:#f6f7fa;padding:10px 12px;border-radius:8px;">
                {safe_url}
              </p>

              <!-- DIVIDER -->
              <hr style="border:0;border-top:1px solid rgba(13,19,32,0.08);margin:0 0 28px;">

              <!-- WHATSAPP NOTE -->
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
                <tr>
                  <td valign="top" width="44" style="padding-right:12px;">
                    <div style="width:36px;height:36px;border-radius:10px;background:rgba(41,211,152,0.14);text-align:center;line-height:36px;font-size:18px;">
                      💬
                    </div>
                  </td>
                  <td valign="top">
                    <p style="margin:0 0 4px;font-size:14px;line-height:1.5;color:#0d1320;font-weight:600;">
                      Em até 12 horas vamos te chamar no WhatsApp.
                    </p>
                    <p style="margin:0;font-size:13px;line-height:1.5;color:#60738f;">
                      Para acompanhar o setup juntos e responder qualquer dúvida.
                    </p>
                  </td>
                </tr>
              </table>

            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td align="center" style="padding:32px 16px 8px;">
              <p style="margin:0 0 8px;font-size:13px;line-height:1.5;color:#60738f;">
                Bem-vindo entre os 20 primeiros. Você é Early Adopter.
              </p>
              <p style="margin:0;font-size:12px;line-height:1.5;color:#94a3b8;">
                — Time OctoBox · <a href="mailto:octobox@octoboxfit.com.br" style="color:#94a3b8;text-decoration:underline;">octobox@octoboxfit.com.br</a>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _html_escape(value: str) -> str:
    """Escape minimo para evitar XSS no HTML do email."""
    if value is None:
        return ''
    return (
        str(value)
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace("'", '&#39;')
    )


__all__ = [
    'build_owner_onboarding_subject',
    'build_owner_onboarding_body',
    'build_owner_onboarding_html_body',
]
