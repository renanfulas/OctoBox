"""
ARQUIVO: templates do email de login (link magico) do corredor de treinos.

POR QUE ELE EXISTE:
- Ate aqui o email de login era texto puro (get_student_email_gateway,
  delivery_gateways.py) — pedido direto do Renan por um email com "cara
  premium", mesmo padrao visual que o email de onboarding do dono de box
  ja usa (signup/notifications.py::build_owner_onboarding_html_body).
- Fica em modulo proprio (nao dentro de public_workout_login.py) pelo
  mesmo motivo de signup/notifications.py: trocar a prosa/visual do email
  nao devia exigir mexer na logica de emissao de token/rate-limit.

O QUE ESTE ARQUIVO FAZ:
1. Gera o subject (sem acento, mesma convencao de build_owner_onboarding_subject
   — maximiza compatibilidade com cliente de email legado).
2. Gera o corpo em texto plano (fallback obrigatorio).
3. Gera o corpo em HTML — table-based, estilo inline (compativel com
   Outlook/Gmail/Apple Mail), mesma estrutura ja validada em producao por
   build_owner_onboarding_html_body, so trocando a paleta pra o azul da
   marca Curva (#2451C4, mesmo tom de static/css/public_workouts/landing.css)
   em vez do gradiente rosa/azul do OctoBox — email de aluno de consultoria,
   marca diferente do SaaS de box (ver landing.css: "marca propria, accent
   definido aqui, independente do accent por aluno do corredor autenticado").

PONTOS CRITICOS:
- Sem foto/imagem embutida de proposito: nao ha asset de foto real da Curva
  neste repo (so screenshots do produto OctoBox, que seriam a marca errada
  aqui) — o "premium" vem de tipografia/espaco/cor, mesmo recurso que o
  email do OctoBox ja usa antes mesmo do CTA. Se/quando houver foto real
  (do Renan, da Giovanna, do box), da pra encaixar como header da HERO CARD
  sem mudar a estrutura.
- `_html_escape` duplicado de signup/notifications.py de proposito (import
  cross-app so por isso seria acoplamento desnecessario pra uma funcao de
  3 linhas sem estado).
"""

from __future__ import annotations


def build_login_email_subject() -> str:
    """Sem acento no subject — mesma convencao de build_owner_onboarding_subject."""
    return 'Curva · Seu link de acesso ao treino'


def build_login_email_body(*, login_url: str, expires_in_minutes: int) -> str:
    """Corpo em texto plano — fallback obrigatorio (nem todo cliente renderiza HTML)."""
    return (
        'Toque no link abaixo para entrar no seu treino:\n'
        '\n'
        f'{login_url}\n'
        '\n'
        f'Vale por {expires_in_minutes} minutos. Se voce nao pediu esse link, ignore este email.\n'
        '\n'
        '— Curva Treino & Nutricao\n'
    )


def build_login_email_html_body(*, login_url: str, expires_in_minutes: int) -> str:
    """Versao HTML — mesma estrutura table-based/inline-style ja validada em
    producao por build_owner_onboarding_html_body (signup/notifications.py),
    paleta trocada pro azul da marca Curva."""
    safe_url = _html_escape(login_url)
    return f"""\
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="x-apple-disable-message-reformatting">
<title>Seu link de acesso — Curva</title>
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
    Seu link de acesso ao treino — vale por {expires_in_minutes} minutos.
  </span>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f4f5f7;">
    <tr>
      <td align="center" style="padding:40px 16px;">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" class="container" style="width:600px;max-width:100%;">

          <!-- LOGO -->
          <tr>
            <td align="left" style="padding:0 8px 24px;">
              <span style="display:inline-block;font-weight:800;font-size:20px;letter-spacing:-0.04em;color:#0d1320;">
                Cur<span style="color:#2451C4;">va</span>
              </span>
              <span style="display:inline-block;margin-left:6px;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:#60738f;">
                TREINO &amp; NUTRICAO
              </span>
            </td>
          </tr>

          <!-- HERO CARD -->
          <tr>
            <td class="card" style="background:#ffffff;border-radius:20px;padding:44px 40px;box-shadow:0 24px 60px rgba(15,23,42,0.06);border:1px solid rgba(13,19,32,0.06);">

              <!-- EYEBROW -->
              <p style="margin:0 0 16px;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:#2451C4;font-weight:800;">
                ✦ Seu link de acesso
              </p>

              <!-- HEADLINE -->
              <h1 class="h1" style="margin:0 0 18px;font-size:32px;line-height:1.08;letter-spacing:-0.04em;font-weight:800;color:#0d1320;">
                Bora treinar?
              </h1>

              <!-- BODY -->
              <p style="margin:0 0 28px;font-size:16px;line-height:1.6;color:#3a5371;">
                Toque no botao abaixo pra entrar direto no seu treino — sem senha,
                sem complicacao.
              </p>

              <!-- CTA -->
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 28px;">
                <tr>
                  <td bgcolor="#2451C4" style="border-radius:14px;background:linear-gradient(135deg,#2451C4,#4C74D9);">
                    <a href="{safe_url}" class="cta" style="display:inline-block;padding:16px 28px;font-size:16px;font-weight:700;letter-spacing:-0.01em;color:#ffffff;text-decoration:none;border-radius:14px;">
                      Entrar no treino →
                    </a>
                  </td>
                </tr>
              </table>

              <!-- INFO -->
              <p style="margin:0 0 8px;font-size:13px;line-height:1.5;color:#60738f;">
                O link vale por {expires_in_minutes} minutos. Se preferir, copie e cole no navegador:
              </p>
              <p style="margin:0 0 28px;font-size:12px;line-height:1.5;color:#3a5371;word-break:break-all;font-family:'SF Mono','Menlo','Consolas',monospace;background:#f6f7fa;padding:10px 12px;border-radius:8px;">
                {safe_url}
              </p>

              <!-- DIVIDER -->
              <hr style="border:0;border-top:1px solid rgba(13,19,32,0.08);margin:0 0 28px;">

              <p style="margin:0;font-size:13px;line-height:1.5;color:#60738f;">
                Nao pediu esse link? Pode ignorar este email — ninguem alem de quem
                clicar consegue entrar na sua conta.
              </p>

            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td align="center" style="padding:32px 16px 8px;">
              <p style="margin:0;font-size:12px;line-height:1.5;color:#94a3b8;">
                — Curva Treino &amp; Nutricao · Renan Fulas (CREF 155070-G/SP) · Giovanna Fontes (CRN-3 67286)
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
    """Escape minimo para evitar XSS no HTML do email — mesma logica de
    signup/notifications.py::_html_escape, duplicada de proposito (ver
    docstring do modulo)."""
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
    'build_login_email_subject',
    'build_login_email_body',
    'build_login_email_html_body',
]
