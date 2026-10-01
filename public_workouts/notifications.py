"""
ARQUIVO: avisos de cobranca do corredor de treinos (Onda B2 do CORDA, V4).

POR QUE ELE EXISTE:
- copia a FORMA de finance/payment_notifications.py::notify_payment_confirmed
  (D.00) — mesmo desenho de "por canal, nunca propaga, sempre loga" — mas
  chamando os senders proprios do corredor (student_identity/delivery_gateways.py,
  ja usado pelo login por e-mail da Onda B1), nunca editando finance/.

PONTOS CRITICOS:
- Falha de canal e logada e NUNCA propaga — nao pode derrubar o drain
  (mesma regra do box: "nao pode falhar o webhook", aqui "nao pode falhar
  o drain de avisos").
- So e-mail por enquanto: o corredor ainda nao tem push nem WhatsApp
  proprios (essa infraestrutura e do app do aluno de box). Adicionar
  canal aqui e trabalho de outra onda, nao invencao deste modulo.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from student_identity.delivery_gateways import StudentEmailDeliveryError, get_student_email_gateway

logger = logging.getLogger(__name__)

_STAFF_HTML_ESCAPE = (
    ('&', '&amp;'), ('<', '&lt;'), ('>', '&gt;'), ('"', '&quot;'), ("'", '&#39;'),
)


def _html_escape(value) -> str:
    """Escape minimo — duplicado de proposito de student_identity/public_workout_notifications.py
    (mesma razao: funcao de 3 linhas sem estado, import cross-app seria acoplamento a toa)."""
    text = '' if value is None else str(value)
    for raw, safe in _STAFF_HTML_ESCAPE:
        text = text.replace(raw, safe)
    return text


def _format_brl(amount) -> str:
    """'R$1.234,56' — sem espaco apos o R$ (convencao pedida pro assunto do
    aviso de nova assinatura)."""
    if amount is None:
        return ''
    return f'R${amount:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')


def _latest_paid_amount(subscription):
    """Valor realmente cobrado na ativacao — nunca o preco de tabela do tier,
    pra refletir corretamente preco customizado/negociado (custom_monthly_price)."""
    from .models import PublicWorkoutPaymentStatus

    payment = subscription.payments.filter(
        status=PublicWorkoutPaymentStatus.PAID,
    ).order_by('-paid_at').first()
    if payment is not None:
        return payment.gross_amount
    return subscription.custom_monthly_price


def _previous_status_label(previous_status: str) -> str:
    from .models import PublicWorkoutSubscriptionStatus

    try:
        return PublicWorkoutSubscriptionStatus(previous_status).label
    except ValueError:
        return previous_status or '(desconhecido)'


def _intake_cta_block(safe_intake_url: str) -> str:
    """So o link puro (sem botao) — pensado pro staff copiar e colar no
    WhatsApp, nunca clicar primeiro: o token e' de uso unico, entao abrir
    aqui antes consome o link e quebra o fluxo da aluna. Vazio se nao
    houver link (ex.: PUBLIC_WORKOUT_PUBLIC_BASE_URL ausente, mesma
    degradacao graciosa que o resto deste modulo ja usa pra nao derrubar
    um alerta interno por uma config que nao lhe diz respeito)."""
    if not safe_intake_url:
        return ''
    return f"""\
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 28px;">
                <tr>
                  <td style="padding:0 0 10px;">
                    <p style="margin:0;font-size:11px;letter-spacing:0.16em;text-transform:uppercase;color:#a4afc2;font-weight:700;">
                      Próximo passo
                    </p>
                    <p style="margin:0;font-size:17px;font-weight:700;color:#f3f6fb;letter-spacing:-0.01em;">
                      Responder anamnese
                    </p>
                  </td>
                </tr>
                <tr>
                  <td style="padding:6px 0 0;">
                    <p style="margin:0 0 6px;font-size:13px;line-height:1.5;color:#a4afc2;">
                      Link pessoal dela, de uso único — envie por WhatsApp:
                    </p>
                    <p style="margin:0;font-size:12px;line-height:1.5;color:#a4afc2;word-break:break-all;font-family:'SF Mono','Menlo','Consolas',monospace;background:#0a0e1a;border:1px solid #273044;padding:10px 12px;border-radius:8px;">
                      {safe_intake_url}
                    </p>
                  </td>
                </tr>
              </table>"""


def _build_staff_new_subscription_html(
    *, email: str, tier_label: str, amount_str: str, intake_url: str, previous_status_label: str,
) -> str:
    """Paleta oficial do Curva — as mesmas custom properties documentadas
    em static/css/public_workouts/landing.css (--curva-bg/--curva-surface/
    --curva-accent/etc.), a fonte de verdade da marca, nao a de um e-mail
    anterior (RT pedido explicitamente pelo usuario: "cores padrao no
    estilo curva que esta nos documentos"). Mesma estrutura table-based/
    inline-style de sempre — so' troca a paleta clara pela escura.

    `intake_url` (se presente) e' o link magico de login da PROPRIA aluna
    direto pra anamnese (/treinos/anamnese) — pensado pro staff repassar
    por WhatsApp, nao pra abrir primeiro: o token e' de uso unico (ver
    PublicWorkoutLoginToken.mark_used), entao clicar aqui antes consome o
    link e quebra o fluxo dela."""
    safe_email = _html_escape(email)
    safe_tier = _html_escape(tier_label)
    safe_amount = _html_escape(amount_str)
    safe_previous = _html_escape(previous_status_label)
    safe_intake_url = _html_escape(intake_url)
    amount_row = (
        f"""
              <tr>
                <td style="padding:14px 18px;border-top:1px solid #273044;">
                  <p style="margin:0 0 4px;font-size:11px;letter-spacing:0.16em;text-transform:uppercase;color:#a4afc2;font-weight:700;">
                    Valor
                  </p>
                  <p style="margin:0;font-size:17px;font-weight:700;color:#f3f6fb;letter-spacing:-0.01em;">
                    {safe_amount}/mes
                  </p>
                </td>
              </tr>"""
        if safe_amount else ''
    )
    return f"""\
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="x-apple-disable-message-reformatting">
<title>Nova assinatura — Curva</title>
<style>
  @media (max-width: 620px) {{
    .container {{ width: 100% !important; padding: 24px 16px !important; }}
    .card {{ padding: 28px 22px !important; }}
    .h1 {{ font-size: 26px !important; line-height: 1.15 !important; }}
  }}
</style>
</head>
<body style="margin:0;padding:0;background:#0a0e1a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;color:#f3f6fb;-webkit-font-smoothing:antialiased;">
  <span style="display:none !important;visibility:hidden;mso-hide:all;font-size:1px;color:#0a0e1a;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;">
    Nova assinatura ativa: {safe_email} ({safe_tier}{' · ' + safe_amount if safe_amount else ''}).
  </span>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#0a0e1a;">
    <tr>
      <td align="center" style="padding:40px 16px;">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" class="container" style="width:600px;max-width:100%;">

          <!-- LOGO -->
          <tr>
            <td align="left" style="padding:0 8px 24px;">
              <span style="display:inline-block;font-weight:800;font-size:20px;letter-spacing:-0.04em;color:#f3f6fb;">
                Cur<span style="color:#00e5ff;">va</span>
              </span>
              <span style="display:inline-block;margin-left:6px;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:#a4afc2;">
                TREINO &amp; NUTRIÇÃO
              </span>
            </td>
          </tr>

          <!-- HERO CARD -->
          <tr>
            <td class="card" style="background:#111827;border-radius:20px;padding:44px 40px;box-shadow:0 24px 60px rgba(0,0,0,0.35);border:1px solid #273044;">

              <!-- EYEBROW -->
              <p style="margin:0 0 16px;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:#00e5ff;font-weight:800;">
                ✦ Nova assinatura
              </p>

              <!-- HEADLINE -->
              <h1 class="h1" style="margin:0 0 18px;font-size:32px;line-height:1.08;letter-spacing:-0.04em;font-weight:800;color:#f3f6fb;">
                Fechou! 🎉
              </h1>

              <p style="margin:0 0 28px;font-size:16px;line-height:1.6;color:#a4afc2;">
                Assinatura confirmada e ativa no corredor de treinos.
              </p>

              <!-- RESUMO -->
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 28px;border:1px solid #273044;border-radius:14px;overflow:hidden;">
                <tr>
                  <td style="background:#151f30;padding:14px 18px;">
                    <p style="margin:0 0 4px;font-size:11px;letter-spacing:0.16em;text-transform:uppercase;color:#a4afc2;font-weight:700;">
                      Aluno
                    </p>
                    <p style="margin:0;font-size:17px;font-weight:700;color:#f3f6fb;letter-spacing:-0.01em;">
                      {safe_email}
                    </p>
                  </td>
                </tr>
                <tr>
                  <td style="padding:14px 18px;border-top:1px solid #273044;">
                    <p style="margin:0 0 4px;font-size:11px;letter-spacing:0.16em;text-transform:uppercase;color:#a4afc2;font-weight:700;">
                      Plano
                    </p>
                    <p style="margin:0;font-size:17px;font-weight:700;color:#f3f6fb;letter-spacing:-0.01em;">
                      {safe_tier}
                    </p>
                  </td>
                </tr>{amount_row}
              </table>

              {_intake_cta_block(safe_intake_url)}

              <hr style="border:0;border-top:1px solid #273044;margin:0 0 20px;">

              <p style="margin:0;font-size:13px;line-height:1.5;color:#a4afc2;">
                Status anterior: <strong style="color:#f3f6fb;">{safe_previous}</strong> → <strong style="color:#00e5ff;">Ativo</strong>
              </p>

            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td align="center" style="padding:32px 16px 8px;">
              <p style="margin:0;font-size:12px;line-height:1.5;color:#a4afc2;">
                — Curva Treino &amp; Nutrição · aviso interno, não repasse ao aluno
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

_OFFSET_LABELS = {
    -7: 'Seu pagamento vence em 7 dias',
    -3: 'Seu pagamento vence em 3 dias',
    -1: 'Seu pagamento vence amanha',
    0: 'Seu pagamento vence hoje',
    2: 'Seu treino foi pausado por falta de pagamento',
}


def _send_due_email(payment, offset_days: int) -> str:
    account = payment.subscription.account
    if not account or not account.email:
        return 'skipped'

    subject = _OFFSET_LABELS.get(offset_days, 'Aviso de cobranca — Treinos')
    body = (
        f'{subject}.\n\n'
        f'Valor: R$ {payment.gross_amount}\n'
        f'Vencimento: {payment.due_date.isoformat()}\n'
    )
    get_student_email_gateway().send(subject=subject, body=body, to_email=account.email)
    return 'sent'


def notify_payment_due(payment, offset_days: int) -> dict:
    """Dispara o aviso de cobranca ao aluno. Devolve o status por canal.

    Nunca levanta: quem chama (drain_public_workout_notices) decide o que
    fazer com o resultado — sent_at so e gravado se nenhum canal deu erro.
    """
    result = {'email': 'skipped'}

    try:
        result['email'] = _send_due_email(payment, offset_days)
    except StudentEmailDeliveryError:
        logger.exception('notify_payment_due: falha no e-mail. payment=%s offset_days=%s', payment.id, offset_days)
        result['email'] = 'error'
    except Exception:
        logger.exception(
            'notify_payment_due: falha inesperada no e-mail. payment=%s offset_days=%s', payment.id, offset_days
        )
        result['email'] = 'error'

    return result


def _build_intake_url(subscription, *, base_url: str) -> str:
    """Magic link de login da PROPRIA aluna, ja apontando pra anamnese de
    treino (/treinos/anamnese — whitelisted em _safe_public_workout_next,
    student_identity/public_workout_views.py).

    72h de validade (nao os 15min do link de "entrar agora" — esse aqui
    nasce num e-mail de STAFF, pra ser repassado por WhatsApp quando der,
    nao clicado na hora). Vazio se base_url nao estiver configurada: um
    alerta interno de staff nao pode falhar por uma config que serve so
    pra montar um link a mais (mesma regra do resto deste modulo).
    """
    if not base_url:
        return ''
    from .models import PublicWorkoutLoginToken

    token = PublicWorkoutLoginToken.objects.create(
        account=subscription.account,
        expires_at=timezone.now() + timezone.timedelta(hours=72),
    )
    return f'{base_url.rstrip("/")}/treinos/login?token={token.token}&next=/treinos/anamnese'


def notify_staff_new_subscription(subscription, *, previous_status: str, base_url: str = '') -> dict:
    """Avisa a equipe quando uma assinatura do corredor vira ACTIVE.

    Cobre venda nova (PENDING_PAYMENT -> ACTIVE) e reativacao apos
    suspensao/atraso (SUSPENDED/PAST_DUE -> ACTIVE) — quem chama
    (reactivate_subscription) so aciona isto numa transicao de verdade,
    nunca numa renovacao recorrente que ja estava ACTIVE.

    Por destinatario, nunca propaga: um endereco mal configurado nao pode
    impedir os demais de receber, nem derrubar o webhook que confirmou o
    pagamento (mesma regra do resto deste modulo).
    """
    from signup.email_sender import send_html_email

    account = subscription.account
    tier_label = subscription.get_tier_display()
    amount = _latest_paid_amount(subscription)
    amount_str = _format_brl(amount)
    previous_status_label = _previous_status_label(previous_status)
    intake_url = _build_intake_url(subscription, base_url=base_url)

    subject_tier = f'{tier_label} {amount_str}' if amount_str else tier_label
    subject = f'Nova assinatura ativa — {account.email} ({subject_tier})'
    body = (
        f'Assinatura confirmada e ativa.\n\n'
        f'Aluno: {account.email}\n'
        f'Plano: {tier_label}\n'
        + (f'Valor: {amount_str}/mes\n' if amount_str else '')
        + f'Status anterior: {previous_status_label}\n'
        + (
            f'\nProximo passo: responder anamnese — link pessoal dela, de uso '
            f'unico, repasse por WhatsApp em vez de abrir primeiro:\n{intake_url}\n'
            if intake_url else ''
        )
    )
    html_body = _build_staff_new_subscription_html(
        email=account.email, tier_label=tier_label, amount_str=amount_str,
        intake_url=intake_url, previous_status_label=previous_status_label,
    )
    result = {}
    for staff_email in getattr(settings, 'PUBLIC_WORKOUT_STAFF_ALERT_EMAILS', []):
        try:
            send_html_email(subject=subject, text_body=body, html_body=html_body, to_email=staff_email)
            result[staff_email] = 'sent'
        except Exception:
            logger.exception(
                'notify_staff_new_subscription: falha no e-mail. subscription=%s staff_email=%s',
                subscription.pk, staff_email,
            )
            result[staff_email] = 'error'
    return result


def notify_program_ready(program, *, base_url: str) -> bool:
    """Envia uma unica vez o link autenticavel do programa publicado.

    A publicacao ja foi confirmada quando esta funcao roda. Falha de e-mail
    fica registrada e nunca desfaz o snapshot do treino.
    """
    from public_workouts.models import (
        PublicWorkoutLoginToken,
        PublicWorkoutProgramDelivery,
        PublicWorkoutSubscription,
    )

    subscription = PublicWorkoutSubscription.objects.select_related('account').filter(plan_slug=program.slug).first()
    if subscription is None:
        return False

    with transaction.atomic():
        delivery, _created = PublicWorkoutProgramDelivery.objects.select_for_update().get_or_create(program=program)
        if delivery.sent_at is not None:
            return True
        delivery.attempted_at = timezone.now()
        delivery.attempt_count += 1
        delivery.last_error = ''
        delivery.save(update_fields=['attempted_at', 'attempt_count', 'last_error'])

    token = PublicWorkoutLoginToken.objects.create(
        account=subscription.account,
        expires_at=timezone.now() + timezone.timedelta(minutes=15),
    )
    login_url = f'{base_url.rstrip("/")}/treinos/login?token={token.token}&next=/renan/{program.slug}'
    subject = 'Seu programa Curva esta pronto'
    body = (
        'Seu programa foi revisado e publicado.\n\n'
        f'Acesse com seguranca: {login_url}\n\n'
        'O link vale por 15 minutos. Se expirar, solicite outro na tela de login.'
    )
    try:
        get_student_email_gateway().send(subject=subject, body=body, to_email=subscription.account.email)
    except Exception as exc:
        logger.exception('notify_program_ready: falha no e-mail. program=%s', program.pk)
        PublicWorkoutProgramDelivery.objects.filter(program=program).update(last_error=str(exc)[:255])
        return False

    PublicWorkoutProgramDelivery.objects.filter(program=program).update(sent_at=timezone.now(), last_error='')
    return True


def notify_meal_plan_ready(meal_plan, *, base_url: str) -> bool:
    from public_workouts.models import (
        PublicWorkoutLoginToken,
        PublicWorkoutMealPlanDelivery,
        PublicWorkoutSubscription,
    )

    subscription = PublicWorkoutSubscription.objects.select_related('account').filter(
        account=meal_plan.account,
    ).first()
    if subscription is None:
        return False

    with transaction.atomic():
        delivery, _created = PublicWorkoutMealPlanDelivery.objects.select_for_update().get_or_create(
            meal_plan=meal_plan,
        )
        if delivery.sent_at is not None:
            return True
        delivery.attempted_at = timezone.now()
        delivery.attempt_count += 1
        delivery.last_error = ''
        delivery.save(update_fields=['attempted_at', 'attempt_count', 'last_error'])

    token = PublicWorkoutLoginToken.objects.create(
        account=subscription.account,
        expires_at=timezone.now() + timezone.timedelta(minutes=15),
    )
    login_url = f'{base_url.rstrip("/")}/treinos/login?token={token.token}&next=/treinos/minha-conta'
    try:
        get_student_email_gateway().send(
            subject='Seu plano alimentar Curva esta pronto',
            body=(
                'Seu plano alimentar foi revisado e publicado.\n\n'
                f'Acesse com seguranca: {login_url}\n\n'
                'O link vale por 15 minutos.'
            ),
            to_email=subscription.account.email,
        )
    except Exception as exc:
        logger.exception('notify_meal_plan_ready: falha no e-mail. meal_plan=%s', meal_plan.pk)
        PublicWorkoutMealPlanDelivery.objects.filter(meal_plan=meal_plan).update(last_error=str(exc)[:255])
        return False

    PublicWorkoutMealPlanDelivery.objects.filter(meal_plan=meal_plan).update(
        sent_at=timezone.now(), last_error='',
    )
    return True


def notify_waitlist_invitation(entry, *, base_url: str) -> bool:
    """Convida sem colocar PII ou token reutilizavel na URL."""
    from public_workouts.models import PublicWorkoutWaitlistStatus

    if entry.status == PublicWorkoutWaitlistStatus.CONVERTED:
        return True
    landing_url = f'{base_url.rstrip("/")}/treinos/?invite={entry.invite_token}#curva-precos'
    try:
        get_student_email_gateway().send(
            subject='Sua vaga no Curva esta disponivel',
            body=(
                f'Abrimos uma vaga para o plano {entry.get_tier_display()} que voce escolheu.\n\n'
                f'Contrate por aqui: {landing_url}\n\n'
                'A disponibilidade e limitada e sera revalidada no checkout.'
            ),
            to_email=entry.email,
        )
    except Exception:
        logger.exception('notify_waitlist_invitation: falha no e-mail. entry=%s', entry.pk)
        return False
    entry.status = PublicWorkoutWaitlistStatus.INVITED
    entry.invited_at = timezone.now()
    entry.expires_at = timezone.now() + timezone.timedelta(days=3)
    entry.save(update_fields=['status', 'invited_at', 'expires_at', 'updated_at'])
    return True


__all__ = [
    'notify_meal_plan_ready', 'notify_payment_due', 'notify_program_ready',
    'notify_staff_new_subscription', 'notify_waitlist_invitation',
]
