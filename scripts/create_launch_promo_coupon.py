"""Cria o Coupon + Promotion Code da campanha "1o mes gratis" na Stripe.

Idempotente: se ja existir uma Promotion Code ativa com o codigo configurado,
so imprime o ID dela em vez de criar duplicata.

So aplicavel ao plano MENSAL (ver signup/services.py:_resolve_launch_promotion_code_id) —
100% off, duration=once, e por isso nunca deve ser oferecido no plano anual.

Uso (mesma chave STRIPE_SECRET_KEY do .env — rode com a chave de TEST antes
de rodar contra a chave LIVE):
  manage.py shell --command "exec(open(r'scripts/create_launch_promo_coupon.py', encoding='utf-8').read())"

Depois de rodar, copie o ID impresso ("promo_...") para STRIPE_LAUNCH_PROMOTION_CODE_ID no .env.
"""
from django.conf import settings

promo_code = (getattr(settings, 'STRIPE_LAUNCH_PROMO_CODE', '') or '').strip().upper()
secret_key = (getattr(settings, 'STRIPE_SECRET_KEY', '') or '').strip()

if not promo_code:
    raise SystemExit('STRIPE_LAUNCH_PROMO_CODE nao definido no .env — defina o codigo da campanha antes de rodar.')
if not secret_key:
    raise SystemExit('STRIPE_SECRET_KEY nao definido no .env.')

import stripe  # noqa: E402 (import tardio, so quando as validacoes acima passam)

stripe.api_key = secret_key

existing = stripe.PromotionCode.list(code=promo_code, limit=1)
if existing.data:
    promotion_code = existing.data[0]
    print(f'Promotion Code "{promo_code}" ja existe: {promotion_code.id} (ativa={promotion_code.active})')
else:
    coupon = stripe.Coupon.create(
        name=f'Campanha {promo_code} — 1o mes gratis',
        percent_off=100,
        duration='once',
    )
    # stripe-python >= ~13: PromotionCode.create espera o cupom aninhado em
    # `promotion={'type': 'coupon', 'coupon': ...}`, nao mais `coupon=...` na
    # raiz (a API rejeita com "Received unknown parameter: coupon"). Achado
    # rodando este fluxo contra a Stripe live em 2026-09-09.
    promotion_code = stripe.PromotionCode.create(
        promotion={'type': 'coupon', 'coupon': coupon.id},
        code=promo_code,
        max_redemptions=200,
    )
    print(f'Coupon criado: {coupon.id}')
    print(f'Promotion Code criada: {promotion_code.id} (code={promo_code})')

print()
print('Cole isto no .env:')
print(f'STRIPE_LAUNCH_PROMOTION_CODE_ID={promotion_code.id}')
