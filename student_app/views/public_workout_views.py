"""
ARQUIVO: corredor publico de treinos em modo PWA.

POR QUE ELE EXISTE:
- separa os links publicos sem login da fronteira autenticada do app do aluno.

O QUE ESTE ARQUIVO FAZ:
1. entrega paginas HTML e endpoints do corredor Curva.
2. reexporta temporariamente catalogo, acesso e views PWA para URLs legadas.

PONTOS CRITICOS:
- roda no schema `public` sem tenant (ver PUBLIC_SCHEMA_PATHS em
  control/middleware.py): NENHUMA view aqui pode tocar modelo de
  TENANT_APPS. O conftest aplica schema_context('box_test') nos testes,
  entao esse erro passa no teste e so quebra em producao.
- usa render_to_string SEM request de proposito. render(request, ...)
  dispararia access.context_processors.role_navigation, que consulta o
  banco com usuario anonimo no schema public.
- `slug` e `store_key` de PublicWorkoutPlan sao congelados: o primeiro
  esta em links ja distribuidos, o segundo e o namespace do localStorage
  onde o aluno guarda o historico de carga.
"""

from __future__ import annotations

import json

from django.conf import settings
from django.http import Http404, HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.views.generic import View

from public_workouts.catalog import (
    PublicWorkoutAccent, PublicWorkoutPlan, PUBLIC_WORKOUT_LIBRARY,
    _TAB_TREINO, _TAB_AVALIACOES,
)
from .public_workout_pwa import (
    PUBLIC_WORKOUT_SCOPE, PUBLIC_WORKOUT_OFFLINE_URL, PUBLIC_WORKOUT_CACHE_EPOCH,
    PUBLIC_WORKOUT_ICON_192, PUBLIC_WORKOUT_ICON_512,
    PUBLIC_WORKOUT_ICON_MASKABLE_512, PUBLIC_WORKOUT_APPLE_TOUCH_ICON,
    PUBLIC_WORKOUT_STATIC_ASSETS, PUBLIC_WORKOUT_STYLESHEETS, PUBLIC_WORKOUT_SCRIPTS,
    PUBLIC_WORKOUT_UNIFIED_TEMPLATE_STYLESHEETS, PUBLIC_WORKOUT_UNIFIED_TEMPLATE_SCRIPTS,
    public_workout_asset_version, PublicWorkoutManifestView,
    PublicWorkoutServiceWorkerView, PublicWorkoutOfflineView,
)
from .public_workout_access import (
    PUBLIC_WORKOUT_OWNER_COOKIE, PUBLIC_WORKOUT_OWNER_COOKIE_SALT,
    PUBLIC_WORKOUT_OWNER_COOKIE_MAX_AGE, _synthesize_public_workout_plan,
    _get_public_workout_entry, _confirm_subscription_active_or_404,
    _confirm_ownership_or_404, _confirm_login_session_owns_slug_or_404,
    get_public_workout_owner_slug,
)


def _render_public_workout_html(
    plan_slug: str, *, account_id: int | None = None,
) -> str:
    """Renderiza `/renan/<slug>` pelo template unico (`public_workouts/workout.html`).
    Os arquivos HTML por aluno foram removidos: sem `PublicWorkoutProgram`
    ativo nao ha pagina (PublicWorkoutDetailView leva o dono a Minha conta).

    Import tardio de `public_workouts.services`: este modulo e importado
    POR `public_workouts` (`PUBLIC_WORKOUT_LIBRARY`), um import no topo
    criaria ciclo — mesmo motivo documentado em
    `_confirm_login_session_owns_slug_or_404`.

    `account_id=None` (visitante sem sessao B1 resolvida ainda) degrada
    para `trends_by_movement`/`one_rep_max_by_movement`/`load_history`
    vazios — nunca quebra a pagina, so mostra a aba Cargas sem historico.
    """
    plan = _get_public_workout_entry(plan_slug)

    from public_workouts.models import PublicWorkoutAccount, PublicWorkoutSubscription
    from public_workouts.push import configured as curva_push_configured
    from public_workouts.progress_snapshot import build_progress_snapshots
    from public_workouts.services import (
        build_movement_label_lookup,
        build_student_package,
        build_weekly_review,
        get_active_program,
        list_load_history,
        list_program_versions,
        require_nutrition_tier,
    )

    program = get_active_program(slug=plan.slug)
    if program is None:
        raise Http404('Treino publico nao encontrado.')

    guided_session = None
    if account_id is not None:
        from public_workouts.training_sessions import active_session

        guided_session = active_session(account_id=account_id, plan_slug=plan.slug)
        if guided_session is not None and guided_session.program is not None:
            # A ficha publicada depois do início não muda as séries em andamento.
            program = guided_session.program.payload

    if account_id is not None:
        # only_active=True: esta lista alimenta o TEMPLATE (curva,
        # recorde, eco de hoje) -- nunca deve mostrar um registro que ja
        # foi corrigido (Fase 3 do plano curva-carga-completa-...).
        load_history = list_load_history(account_id=account_id, only_active=True)
        # UMA chamada por request (plano curva-grafico-hierarquia-e-set-
        # role.md, §7.5) -- nunca uma por movimento. movement_load_display
        # (sugestao de carga) le daqui em vez de escanear load_history
        # bruto por conta propria.
        progress_snapshots = build_progress_snapshots(account_id=account_id)
        weekly_review = build_weekly_review(account_id=account_id, progress_snapshots=progress_snapshots)
        package = build_student_package(
            account_id=account_id, slug=plan.slug, progress_snapshots=progress_snapshots,
        )
        subscription = PublicWorkoutSubscription.objects.filter(account_id=account_id).first()
        nutrition_unlocked = bool(subscription and require_nutrition_tier(subscription))
        # Com stripe_customer_id (1o checkout ja concluido, webhook ja fez
        # link_stripe_ids): manda pro Customer Portal de verdade, igual ao
        # botao "Gerenciar assinatura" de minha_conta.html (mesmo endpoint
        # POST /treinos/billing-portal, mesmo account.js).
        #
        # Sem stripe_customer_id: achado real (Rafael, cliente legado que
        # ainda paga por fora) -- a assinatura ja nasce com status=ACTIVE
        # (seed_legacy_workout_accounts), entao get_customer_journey() nunca
        # cai nos estados payment_problem/payment_pending, e o hub /treinos/
        # minha-conta nao mostra NADA sobre pagamento. "Pagamentos" caia num
        # link morto pra esse hub. Agora: se o Renan ja' preencheu
        # custom_monthly_price no admin (PublicWorkoutSubscriptionAdmin),
        # mostra um botao de self-service que dispara POST /treinos/
        # checkout-personalizado (PublicWorkoutCustomCheckoutView) -- fecha
        # o loop sem ele precisar copiar/colar link no WhatsApp. Sem o valor
        # definido ainda, mostra "Fale com o Renan" em vez de um link morto
        # ou um botao que sempre falharia.
        billing_portal_available = bool(subscription and subscription.stripe_customer_id)
        custom_checkout_available = bool(
            subscription and not billing_portal_available and subscription.custom_monthly_price is not None
        )
        payment_setup_pending = bool(
            subscription and not billing_portal_available and not custom_checkout_available
        )
        account_email = subscription.account.email if subscription else None
        # None = ainda nao viu o wizard de primeiro login (PublicWorkoutAccount.
        # onboarding_completed_at) — so' dispara quando ha sessao de LOGIN de
        # verdade (B1), nunca pro cookie de posse (B0) de quem so abriu o
        # link: o wizard ensina a USAR a conta (registrar carga, pagamento),
        # nao faz sentido pra quem ainda nem provou que e' dono dela.
        show_onboarding_wizard = (
            PublicWorkoutAccount.objects.filter(pk=account_id, onboarding_completed_at__isnull=True).exists()
        )
    else:
        weekly_review = {'trends_by_movement': {}}
        package = {'one_rep_max_by_movement': {}}
        load_history = []
        progress_snapshots = {}
        nutrition_unlocked = False
        billing_portal_available = False
        custom_checkout_available = False
        payment_setup_pending = False
        account_email = None
        show_onboarding_wizard = False

    program_versions = list_program_versions(slug=plan.slug)
    active_program_version = (
        guided_session.program.version if guided_session is not None and guided_session.program is not None
        else next((row['version'] for row in program_versions if row['is_active']), None)
    )
    asset_version = public_workout_asset_version()
    return render_to_string('public_workouts/workout.html', {
        'asset_version': asset_version,
        'plan_slug': plan.slug,
        'accent_variant': plan.assessment_sex,
        'program': program,
        'program_versions': program_versions,
        'active_program_version': active_program_version,
        'load_history': load_history,
        'progress_snapshots': progress_snapshots,
        'one_rep_max_by_movement': package['one_rep_max_by_movement'],
        'trends_by_movement': weekly_review['trends_by_movement'],
        'movement_labels': build_movement_label_lookup(program),
        'student_name': plan.short_name,
        'student_photo_url': None,
        'billing_portal_available': billing_portal_available,
        'custom_checkout_available': custom_checkout_available,
        'payment_setup_pending': payment_setup_pending,
        'account_email': account_email,
        'guided_account_scope': account_id or '',
        'nutrition_unlocked': nutrition_unlocked,
        'show_onboarding_wizard': show_onboarding_wizard,
        'push_public_key': getattr(settings, 'STUDENT_WEB_PUSH_VAPID_PUBLIC_KEY', '').strip(),
        'push_configured': curva_push_configured(),
    })


def _render_payment_blocked_html(plan: PublicWorkoutPlan) -> str:
    """Tela de "pagamento pendente" — achado real (feedback do Renan): 404
    silencioso e' certo pra quem NAO e' dono (nunca revela que o slug de
    outra pessoa existe), mas e' errado pro PROPRIO dono, que so' quer
    saber por que parou de ver o treino e como resolver. Sem firula: um
    botao que abre o Customer Portal da Stripe (PublicWorkoutBillingPortalView,
    ja existente) — a pessoa atualiza o cartao/paga o que falta por conta
    propria, o webhook de invoice.payment_succeeded (billing.py::
    record_successful_invoice_payment) reativa a assinatura sozinho."""
    return render_to_string('public_workouts/payment_blocked.html', {
        'student_name': plan.short_name,
    })


def _public_workout_login_redirect(plan_slug: str):
    response = redirect(f'/treinos/login?next=/renan/{plan_slug}')
    response['X-Robots-Tag'] = 'noindex, nofollow'
    return response


def _private_public_workout_response(html: str) -> HttpResponse:
    """Pagina pessoal do aluno: nunca em cache compartilhado nem em buscador."""
    response = HttpResponse(html)
    response['Cache-Control'] = 'private, no-store'
    response['X-Robots-Tag'] = 'noindex, nofollow'
    return response


class PublicWorkoutDetailView(View):
    def get(self, request, plan_slug, *args, **kwargs):
        plan = _get_public_workout_entry(plan_slug)
        from django.utils import timezone
        from public_workouts.acquisition import record_funnel_event
        from public_workouts.models import (
            PublicWorkoutAcquisitionSession,
            PublicWorkoutMealPlan,
            PublicWorkoutMealPlanDelivery,
            PublicWorkoutProgram,
            PublicWorkoutProgramDelivery,
            PublicWorkoutSubscription,
        )
        from student_identity.public_workout_session import get_public_workout_account_id_from_request

        # A pagina traz nome, avaliacao corporal e historico do aluno: posse
        # do link nao prova identidade (o slug e' o primeiro nome). Todo
        # slug exige sessao de login, com ou sem `requires_login`.
        if get_public_workout_account_id_from_request(request) is None:
            return _public_workout_login_redirect(plan.slug)
        _confirm_ownership_or_404(request, plan.slug)
        # get_token() marca o cookie CSRF pra ser enviado na resposta —
        # sem isso, o cookie nunca nasce aqui (nenhum template desta pagina
        # usa {% csrf_token %}) e o JS de escrita (autoavaliacao online,
        # assessments.js) nunca teria um X-CSRFToken valido pra mandar no
        # POST de /avaliacoes: 403 sempre, em qualquer navegador de verdade.
        from django.middleware.csrf import get_token

        get_token(request)

        # Os clientes legados (seed_legacy_workout_accounts) entram pelo
        # mesmo login por e-mail dos demais; a sessao ja foi exigida acima.
        from public_workouts.models import PublicWorkoutSubscriptionStatus
        from student_identity.public_workout_session import renew_public_workout_session_cookie_if_stale

        account_id = get_public_workout_account_id_from_request(request)

        # Pagamento bloqueado: tela dedicada (nao 404) — ver docstring de
        # _render_payment_blocked_html. So' se aplica quando EXISTE
        # assinatura pra este slug e ela nao esta ACTIVE (mesma condicao
        # de _confirm_subscription_active_or_404, so' que aqui vira tela
        # em vez de excecao — os 10 clientes legados sem assinatura Stripe
        # nenhuma nunca caem neste ramo).
        blocking_subscription = (
            PublicWorkoutSubscription.objects.filter(plan_slug=plan.slug)
            .exclude(status=PublicWorkoutSubscriptionStatus.ACTIVE)
            .exists()
        )
        if blocking_subscription:
            response = _private_public_workout_response(_render_payment_blocked_html(plan))
            return renew_public_workout_session_cookie_if_stale(request, response)

        from public_workouts.services import get_active_program

        if get_active_program(slug=plan.slug) is None:
            # Pago e logado, mas o programa ainda nao foi publicado: Minha conta
            # mostra "programa em preparacao" em vez de uma pagina vazia.
            response = redirect('public-workout-account')
            response['X-Robots-Tag'] = 'noindex, nofollow'
            return response

        # O cliente do PWA envia POSTs JSON para sessão/push via cookie CSRF.
        # Força o cookie também nas páginas renderizadas por render_to_string.
        get_token(request)
        response = _private_public_workout_response(_render_public_workout_html(
            plan_slug, account_id=account_id,
        ))
        opened_subscription = PublicWorkoutSubscription.objects.select_related('account').filter(
            plan_slug=plan.slug, account_id=account_id,
        ).first()
        if opened_subscription is not None:
            active_program = PublicWorkoutProgram.objects.filter(
                slug=plan.slug, is_active=True,
            ).first()
            if active_program is not None:
                PublicWorkoutProgramDelivery.objects.filter(
                    program=active_program, opened_at__isnull=True,
                ).update(opened_at=timezone.now())
            record_funnel_event(
                'program_opened',
                acquisition_session=PublicWorkoutAcquisitionSession.objects.filter(
                    subscription=opened_subscription,
                ).first(),
                account=opened_subscription.account,
                subscription=opened_subscription,
                tier=opened_subscription.tier,
            )
        renew_public_workout_session_cookie_if_stale(request, response)
        # B0: so o dono logado chega aqui — e o que autoriza a leitura de
        # /avaliacoes.json a seguir. Cookie por instancia, nao global: cada
        # slug so autoriza a si mesmo.
        response.set_signed_cookie(
            PUBLIC_WORKOUT_OWNER_COOKIE,
            plan.slug,
            salt=PUBLIC_WORKOUT_OWNER_COOKIE_SALT,
            max_age=PUBLIC_WORKOUT_OWNER_COOKIE_MAX_AGE,
            httponly=True,
            samesite='Lax',
            secure=not settings.DEBUG,
        )
        return response


class PublicWorkoutPreviewView(View):
    """GET /renan/<slug>/preview — Onda B3: renderiza o template unico
    (`workout.html`) contra dado PUBLICADO de verdade (`PublicWorkoutProgram`),
    sem tocar a rota real (`/renan/<slug>`, PublicWorkoutDetailView, que
    continua servindo o template legado ate a B3 decidir fase de acesso
    e corte). Existe so pra comparacao lado a lado antes do corte real de
    verdade — nunca linkada em nenhum lugar do produto, mesmo nivel de
    exposicao da pagina de hoje (quem sabe a URL, ve; B3 item 6, login
    obrigatorio, ainda nao esta ligado).

    PONTOS CRITICOS:
    - Mesmo gate de posse da rota real (`_confirm_login_session_owns_slug_or_404`):
      sessao de OUTRO aluno logado recebe 404, nunca o treino de outra
      pessoa.
    - Consulta so `PublicWorkoutProgram` — nunca `PUBLIC_WORKOUT_LIBRARY`
      (o dict por-plano que a rota legada usa pra achar `template_file`):
      a proposta da B3 e justamente parar de depender dele.
    - Dado pessoal (historico de carga, 1RM, versoes, tendencia) so
      aparece quando ha sessao de LOGIN ativa (Onda B1) dona do slug —
      visitante anonimo ve o programa prescrito, sem historico. Mesma
      limitacao que a pagina de hoje ja tem (o tracker legado tambem e
      so local ao aparelho, nunca sincroniza entre dispositivos).
    - Seta o MESMO cookie de posse do B0 que PublicWorkoutDetailView —
      a aba Avaliacao do template novo e 100% client-side (assessments.js
      -> GET /renan/<slug>/avaliacoes.json, PublicWorkoutAssessmentsView),
      que exige esse cookie. Sem ele, a aba sempre 404 mesmo com o resto
      da pagina funcionando (achado ao verificar visualmente).
    """

    def get(self, request, plan_slug, *args, **kwargs):
        from public_workouts.progress_snapshot import build_progress_snapshots
        from public_workouts.push import configured as curva_push_configured
        from public_workouts.services import (
            build_movement_label_lookup,
            build_student_package,
            build_weekly_review,
            get_active_program,
            list_load_history,
            list_program_versions,
        )

        program = get_active_program(slug=plan_slug)
        if program is None:
            raise Http404('Treino publico nao encontrado.')

        from student_identity.public_workout_session import get_public_workout_account_id_from_request

        # Mesma regra da rota real: o cookie de posse abaixo libera
        # /avaliacoes.json, entao nunca sai para visitante sem login.
        if get_public_workout_account_id_from_request(request) is None:
            return _public_workout_login_redirect(plan_slug)
        _confirm_login_session_owns_slug_or_404(request, plan_slug)

        # Mesmo cookie de posse do B0 que PublicWorkoutDetailView ja seta —
        # sem ele, a aba Avaliacao (100% client-side via assessments.js,
        # GET /renan/<slug>/avaliacoes.json) sempre 404 aqui, mesmo com o
        # resto da pagina funcionando. get_token() pelo mesmo motivo de la:
        # marca o cookie CSRF pro POST de autoavaliacao online funcionar.
        from django.middleware.csrf import get_token

        get_token(request)

        account_id = get_public_workout_account_id_from_request(request)
        load_history: list = []
        progress_snapshots: dict = {}
        one_rep_max_by_movement: dict = {}
        trends_by_movement: dict = {}
        account_email = None
        if account_id is not None:
            # only_active=True: esta lista alimenta o TEMPLATE (curva,
            # recorde, eco de hoje) -- nunca deve mostrar um registro que
            # ja foi corrigido (Fase 3 do plano curva-carga-completa-...).
            load_history = list_load_history(account_id=account_id, only_active=True)
            # UMA chamada por request -- ver nota equivalente em
            # PublicWorkoutDetailView.
            progress_snapshots = build_progress_snapshots(account_id=account_id)
            one_rep_max_by_movement = build_student_package(
                account_id=account_id, slug=plan_slug, progress_snapshots=progress_snapshots,
            )['one_rep_max_by_movement']
            trends_by_movement = build_weekly_review(
                account_id=account_id, progress_snapshots=progress_snapshots,
            )['trends_by_movement']

            from public_workouts.models import PublicWorkoutAccount

            account_email = PublicWorkoutAccount.objects.filter(pk=account_id).values_list('email', flat=True).first()

        program_versions = list_program_versions(slug=plan_slug)
        active_program_version = next((row['version'] for row in program_versions if row['is_active']), None)
        html = render_to_string('public_workouts/workout.html', {
            'asset_version': public_workout_asset_version(),
            'program': program,
            'accent_variant': program.get('accent_variant'),
            'program_versions': program_versions,
            'active_program_version': active_program_version,
            'load_history': load_history,
            'progress_snapshots': progress_snapshots,
            'one_rep_max_by_movement': one_rep_max_by_movement,
            'trends_by_movement': trends_by_movement,
            'plan_slug': plan_slug,
            'movement_labels': build_movement_label_lookup(program),
            'account_email': account_email,
            'push_public_key': getattr(settings, 'STUDENT_WEB_PUSH_VAPID_PUBLIC_KEY', '').strip(),
            'push_configured': curva_push_configured(),
        })
        response = _private_public_workout_response(html)
        response.set_signed_cookie(
            PUBLIC_WORKOUT_OWNER_COOKIE,
            plan_slug,
            salt=PUBLIC_WORKOUT_OWNER_COOKIE_SALT,
            max_age=PUBLIC_WORKOUT_OWNER_COOKIE_MAX_AGE,
            httponly=True,
            samesite='Lax',
            secure=not settings.DEBUG,
        )
        return response


class PublicWorkoutTemplatePreviewView(View):
    """GET /renan/<slug>/preview-b3 — preview do template unico (Onda B3,
    `templates/public_workouts/workout.html`) contra o payload JA
    PUBLICADO do slug.

    So' responde com `settings.DEBUG=True` (404 em producao) — o proprio
    `workout.html` documenta que ainda nao esta ligado a nenhuma rota real
    (fase de acesso/hard reset/sw.js novo da Onda B3 real ainda faltam).
    Existe so' pra nao depender de gerar HTML na mao via `manage.py shell`
    toda vez que alguem quer conferir o trabalho em andamento — nunca serve
    trafego de aluno de verdade, nunca precisa do cookie de posse B0.

    Se ja existir uma sessao de LOGIN ativa (PublicWorkoutAccount, ex.:
    quem entrou por Google/e-mail em `/treinos/login`), usa o nome/foto/
    e-mail DELA em vez do nome generico do plano — unica forma de
    conferir a foto do Google no avatar antes do corte de producao real
    (rota ainda nao existe, ver docstring acima). Sem sessao, comportamento
    inalterado (nome do plano, sem foto).
    """

    def get(self, request, plan_slug, *args, **kwargs):
        if not settings.DEBUG:
            raise Http404('Preview do template unico so existe em DEBUG.')

        from public_workouts.models import PublicWorkoutAccount
        from public_workouts.services import build_movement_label_lookup, get_active_program, list_program_versions
        from student_identity.public_workout_session import get_public_workout_account_id_from_request

        plan = _get_public_workout_entry(plan_slug)
        program = get_active_program(slug=plan.slug)
        if program is None:
            return HttpResponse(f'"{plan.slug}" ainda nao tem programa publicado (services.publish_program).', status=404)

        student_name = plan.short_name
        student_photo_url = None
        account_email = None
        account_id = get_public_workout_account_id_from_request(request)
        if account_id is not None:
            account = PublicWorkoutAccount.objects.filter(id=account_id).first()
            if account is not None:
                student_name = account.email.split('@')[0]
                student_photo_url = account.photo_url or None
                account_email = account.email

        html = render_to_string('public_workouts/workout.html', {
            'asset_version': public_workout_asset_version(),
            'plan_slug': plan.slug,
            'accent_variant': plan.assessment_sex,
            'program': program,
            'program_versions': list_program_versions(slug=plan.slug),
            'load_history': [],
            'progress_snapshots': {},
            'one_rep_max_by_movement': {},
            'trends_by_movement': {},
            'movement_labels': build_movement_label_lookup(program),
            'student_name': student_name,
            'student_photo_url': student_photo_url,
            'custom_checkout_available': False,
            'payment_setup_pending': False,
            'account_email': account_email,
            # Preview nunca resolve tier/assinatura real (ver docstring da
            # view) — mesmo com sessao de login ativa, nutricao continua
            # bloqueada aqui.
            'nutrition_unlocked': False,
        })
        return HttpResponse(html)


class PublicWorkoutSignOutView(View):
    """POST /renan/<slug>/sair — "Sair da conta" da tela Perfil.

    Apaga os DOIS cookies de identidade do corredor: o cookie de posse
    (PUBLIC_WORKOUT_OWNER_COOKIE, B0 — quem abriu o link primeiro) e o
    cookie de login por e-mail (octobox_treinos_session, Onda B1). A
    docstring original desta view (escrita antes do B1 existir) dizia que
    so' o B0 importava — ficou desatualizada: sem apagar tambem a sessao de
    login, quem clicava "Sair da conta" continuava logado como o mesmo
    PublicWorkoutAccount por baixo, e ao abrir o link de OUTRO aluno recebia
    404 (_confirm_login_session_owns_slug_or_404 nunca deixa a sessao
    logada ver o slug de outra conta) — parecendo "conta trocada" quando na
    verdade nunca saiu de verdade. Achado ao vivo verificando o corredor,
    corrigido aqui: agora quem voltar a abrir /renan/<slug> (qualquer slug)
    ganha o cookie de posse de volta automaticamente, sem carregar
    identidade de login nenhuma.
    """

    def post(self, request, plan_slug, *args, **kwargs):
        from student_identity.public_workout_session import clear_public_workout_session_cookie

        response = redirect('public-workout-offline')
        response.delete_cookie(PUBLIC_WORKOUT_OWNER_COOKIE, samesite='Lax')
        clear_public_workout_session_cookie(response)
        return response


class PublicWorkoutOnboardingCompleteView(View):
    """POST /renan/<slug>/onboarding — marca o wizard de primeiro login
    como visto (workout.html, onboarding.js).

    Mesmo gate de sessao de PublicWorkoutRecordLoadView (401 sem login,
    404 se a sessao e' de outra conta): `onboarding_completed_at` e' um
    dado da CONTA, nunca aceita sem saber com certeza qual conta esta do
    outro lado. Idempotente por natureza (so seta se ainda None) — o
    wizard pode chamar isto mais de uma vez (clique duplo, retry de
    rede) sem acender `onboarding_completed_at` de novo a cada vez.
    """

    def post(self, request, plan_slug, *args, **kwargs):
        plan = _get_public_workout_entry(plan_slug)

        from django.utils import timezone

        from public_workouts.models import PublicWorkoutAccount
        from student_identity.public_workout_session import get_public_workout_account_id_from_request

        account_id = get_public_workout_account_id_from_request(request)
        if account_id is None:
            return JsonResponse({'error': 'login necessario'}, status=401)

        _confirm_login_session_owns_slug_or_404(request, plan.slug)

        PublicWorkoutAccount.objects.filter(
            pk=account_id, onboarding_completed_at__isnull=True,
        ).update(onboarding_completed_at=timezone.now())
        return JsonResponse({'ok': True})


class PublicWorkoutLocalStorageBackupView(View):
    """POST /renan/<slug>/backup-carga — sobe o blob bruto do localStorage.

    Item 1.7 / F-B do plano de produto (Onda B1 do CORDA): salva o blob
    ANTES do hard reset da Onda B3, sem normalizar — isso fica para depois
    (Onda 3.5). O localStorage e a UNICA copia que existe hoje; perder o
    navegador sem backup e perda permanente.

    Mesmo cookie de posse do B0: sem ele, 404 — nao revela se o slug
    existe, e evita que qualquer terceiro grave lixo associado a um slug
    alheio.
    """

    def post(self, request, plan_slug, *args, **kwargs):
        plan = _get_public_workout_entry(plan_slug)

        if get_public_workout_owner_slug(request) != plan.slug:
            raise Http404('Treino publico nao encontrado.')

        try:
            raw_blob = json.loads(request.body.decode('utf-8') or '{}')
        except (json.JSONDecodeError, UnicodeDecodeError):
            return HttpResponse(status=400)
        if not isinstance(raw_blob, dict):
            return HttpResponse(status=400)

        from public_workouts.models import PublicWorkoutLocalStorageBackup

        PublicWorkoutLocalStorageBackup.objects.create(
            plan_slug=plan.slug,
            store_key=plan.store_key or '',
            raw_blob=raw_blob,
        )
        return JsonResponse({'status': 'ok'})


def _decimal_or_none(value):
    if value is None:
        return None
    from decimal import Decimal, InvalidOperation

    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f'valor numerico invalido: {value!r}') from exc
    # json.loads aceita os literais NaN/Infinity/-Infinity (extensao nao
    # padrao) -- Decimal(str(float('inf'))) constroi sem erro, entao sem
    # este cheque um payload assim passaria pra frente como Decimal nao
    # finito (Decimal('NaN') < 0 levanta InvalidOperation mais na frente,
    # virando 500 em vez de 400).
    if not result.is_finite():
        raise ValueError(f'valor numerico invalido: {value!r}')
    return result


def _reps_or_none(value):
    if value is None:
        return None
    # bool e subclasse de int em Python -- isinstance(True, int) e True,
    # entao o cheque de bool precisa vir antes, senao reps=true viraria
    # reps=1 silenciosamente.
    if isinstance(value, bool):
        raise ValueError(f'reps precisa ser um numero inteiro: {value!r}')
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    raise ValueError(f'reps precisa ser um numero inteiro: {value!r}')


class PublicWorkoutPackageView(View):
    """GET /renan/<slug>/pacote.json — contrapartida de LEITURA do S3
    (Onda B3, item 8 — base, mesmo espirito da PublicWorkoutRecordLoadView
    que ja e' a contrapartida de escrita). Expoe S2 (`build_student_package`)
    pra conta logada dona do slug: ultima carga por movimento (com 1RM
    estimado de verdade desde a Onda A3), substituicoes e `access_until`.

    PONTOS CRITICOS:
    - Mesma regra de auth do record_load: exige sessao de LOGIN ativa
      (Onda B1) — sem sessao, 401 (nao ha slug pra esconder, o problema e'
      "voce nao esta logado"). Sessao de conta que NAO e dona deste slug:
      404, nunca 403 (mesma regra do gate de posse, Onda B3 item 5).
    - So' leitura: nao aceita corpo, nao muda banco. Idempotente por
      natureza (GET), sem necessidade de idempotency_key.
    """

    def get(self, request, plan_slug, *args, **kwargs):
        plan = _get_public_workout_entry(plan_slug)

        from student_identity.public_workout_session import get_public_workout_account_id_from_request

        account_id = get_public_workout_account_id_from_request(request)
        if account_id is None:
            return JsonResponse({'error': 'login necessario'}, status=401)

        _confirm_login_session_owns_slug_or_404(request, plan.slug)

        from public_workouts.services import build_student_package

        package = build_student_package(account_id=account_id, slug=plan.slug)
        return JsonResponse(package, status=200)


class PublicWorkoutWeeklyReviewView(View):
    """GET /renan/<slug>/revisao-semanal — Entrega 4: pega os sinais
    deterministicos de `build_weekly_review` (S/A3) e tenta transformar em
    texto curto via `weekly_review_ai.get_or_create_cached_review_text`
    (Claude Haiku, no maximo 1 chamada por conta por semana ISO — ver
    docstring de weekly_review_ai.py). Chamado tanto pelo botao manual
    "Gerar revisão" (aba Cargas) quanto automaticamente pelo card da aba
    Início (weekly_review.js) — os dois leem/escrevem a MESMA linha de
    cache pra semana corrente, nunca duplicam a chamada a IA.

    PONTOS CRITICOS:
    - Mesma regra de auth de PublicWorkoutPackageView: sessao de LOGIN
      ativa, 401 sem sessao, 404 se a sessao nao e' dona deste slug.
    - `review_text` pode vir `null` (sem IA configurada, sem sinal, timeout,
      erro) — isso e' resposta 200 valida, nunca 500. A tela sempre tem
      fallback neutro pra esse caso.
    """

    def get(self, request, plan_slug, *args, **kwargs):
        plan = _get_public_workout_entry(plan_slug)

        from student_identity.public_workout_session import get_public_workout_account_id_from_request

        account_id = get_public_workout_account_id_from_request(request)
        if account_id is None:
            return JsonResponse({'error': 'login necessario'}, status=401)

        _confirm_login_session_owns_slug_or_404(request, plan.slug)

        from public_workouts.services import build_weekly_review
        from public_workouts.weekly_review_ai import get_or_create_cached_review_text

        review = build_weekly_review(account_id=account_id)
        review_text = get_or_create_cached_review_text(account_id=account_id, review=review)
        return JsonResponse({'review_text': review_text}, status=200)


class PublicWorkoutMealPlanView(View):
    """GET /renan/<slug>/nutricao.json — le' o plano alimentar ATIVO da
    conta logada (Entrega 6, Fase 4 — docs/plans/
    public-workouts-escala-e-nutricao-corda.md, D.4/D.6).

    PONTOS CRITICOS:
    - Mesma regra de auth de PublicWorkoutPackageView: sessao de LOGIN
      ativa, 401 sem sessao, 404 se a sessao nao e' dona deste slug.
    - Gate de tier (D.4): so' Completo/Premium tem acesso. 404, nunca 403
      -- 403 confirmaria que existe conteudo de nutricao pra aquela conta
      (mesma regra do gate de posse B0/B3). Sem assinatura nenhuma
      tambem cai em 404, nunca 500.
    - `meal_plan: null` (tier qualifica mas ninguem publicou plano ainda)
      e' resposta 200 valida, nunca 404 -- mesmo espirito de
      PublicWorkoutWeeklyReviewView (`review_text: null`).
    """

    def get(self, request, plan_slug, *args, **kwargs):
        plan = _get_public_workout_entry(plan_slug)

        from student_identity.public_workout_session import get_public_workout_account_id_from_request

        account_id = get_public_workout_account_id_from_request(request)
        if account_id is None:
            return JsonResponse({'error': 'login necessario'}, status=401)

        _confirm_login_session_owns_slug_or_404(request, plan.slug)

        from public_workouts.acquisition import record_funnel_event
        from public_workouts.models import (
            PublicWorkoutAcquisitionSession,
            PublicWorkoutMealPlan,
            PublicWorkoutMealPlanDelivery,
            PublicWorkoutSubscription,
        )
        from public_workouts.services import get_active_meal_plan, require_nutrition_tier
        from django.utils import timezone

        subscription = PublicWorkoutSubscription.objects.filter(account_id=account_id).first()
        if subscription is None or not require_nutrition_tier(subscription):
            raise Http404('Nutricao nao disponivel pra este plano.')

        meal_plan = PublicWorkoutMealPlan.objects.filter(account_id=account_id, is_active=True).first()
        if meal_plan is not None:
            PublicWorkoutMealPlanDelivery.objects.filter(
                meal_plan=meal_plan, opened_at__isnull=True,
            ).update(opened_at=timezone.now())
            record_funnel_event(
                'meal_plan_opened',
                acquisition_session=PublicWorkoutAcquisitionSession.objects.filter(
                    subscription=subscription,
                ).first(),
                account=subscription.account, subscription=subscription, tier=subscription.tier,
            )
        return JsonResponse({'meal_plan': get_active_meal_plan(account_id=account_id)}, status=200)


class PublicWorkoutExportDataView(View):
    """GET /renan/<slug>/meus-dados.json — export de dados do titular
    (Onda A3, LGPD/GDPR). Mesma regra de auth dos demais endpoints de
    conta (pacote.json, carga): sessao de LOGIN ativa, 401 sem sessao,
    404 se a sessao nao e' dona deste slug.

    Devolve `public_workouts.services.export_account_data` — conta,
    assinatura, cobrancas, avaliacoes e historico de carga. So' leitura,
    nao aceita corpo, nao muda banco.
    """

    def get(self, request, plan_slug, *args, **kwargs):
        plan = _get_public_workout_entry(plan_slug)

        from student_identity.public_workout_session import get_public_workout_account_id_from_request

        account_id = get_public_workout_account_id_from_request(request)
        if account_id is None:
            return JsonResponse({'error': 'login necessario'}, status=401)

        _confirm_login_session_owns_slug_or_404(request, plan.slug)

        from public_workouts.services import export_account_data

        return JsonResponse(export_account_data(account_id=account_id), status=200)


class PublicWorkoutRecordLoadView(View):
    """POST /renan/<slug>/carga — registra uma carga (S3, record_load,
    Onda A1 Fatia B). Consumido pelo outbox de IndexedDB da Onda B3
    (item 8) — reenvio com a mesma `idempotency_key` nunca duplica.

    PONTOS CRITICOS:
    - Exige sessao de LOGIN ativa (Onda B1) — nao o cookie de posse do B0.
      Carga precisa saber QUEM registrou (`account_id`, decisao de D.5 da
      Fatia B); o cookie de posse so prova "abriu este link", nunca
      identifica a pessoa. Sem sessao: 401 (nao 404 — aqui nao ha slug pra
      esconder, o problema e "voce nao esta logado").
    - Sessao ativa de conta que NAO e dona deste slug: 404, mesma regra
      do gate de posse (Onda B3, item 5) — nunca 403, nunca deixa
      registrar carga associada ao treino de outra pessoa.
    """

    def post(self, request, plan_slug, *args, **kwargs):
        plan = _get_public_workout_entry(plan_slug)

        from student_identity.public_workout_session import get_public_workout_account_id_from_request

        account_id = get_public_workout_account_id_from_request(request)
        if account_id is None:
            return JsonResponse({'error': 'login necessario'}, status=401)

        _confirm_login_session_owns_slug_or_404(request, plan.slug)

        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        except (json.JSONDecodeError, UnicodeDecodeError):
            return HttpResponse(status=400)
        if not isinstance(payload, dict):
            return HttpResponse(status=400)

        movement_slug = payload.get('movement_slug')
        idempotency_key = payload.get('idempotency_key')
        performed_on = payload.get('performed_on')
        if not movement_slug or not idempotency_key or not performed_on:
            return JsonResponse({'error': 'movement_slug, performed_on e idempotency_key sao obrigatorios'}, status=400)

        from public_workouts.models import PublicWorkoutLoadLogSetRole
        from public_workouts.services import (
            LoadCorrectionConflictError,
            LoadCorrectionNotFoundError,
            LoadValueError,
            active_correction_successor,
            correct_load,
            record_load,
        )

        # Fase 3 do plano curva-carga-completa-reps-rir-recorde (§4.1):
        # MESMO endpoint, campo opcional novo -- supersedes_idempotency_key
        # presente vira uma correcao (nao um registro novo). movement_slug/
        # performed_on do payload sao ignorados nesse caminho de proposito
        # (correct_load herda os dois do ALVO) -- so' continuam obrigatorios
        # aqui em cima pra manter o contrato de payload simples pro cliente,
        # que ja os manda de qualquer forma (mesmo widget, mesmo contexto).
        supersedes_key = payload.get('supersedes_idempotency_key')

        try:
            if supersedes_key:
                result = correct_load(
                    account_id=account_id,
                    supersedes_idempotency_key=supersedes_key,
                    idempotency_key=idempotency_key,
                    weight_kg=_decimal_or_none(payload.get('weight_kg')),
                    reps=_reps_or_none(payload.get('reps')),
                    rir=_decimal_or_none(payload.get('rir')),
                )
            else:
                # Protocolo de payload (plano curva-grafico-hierarquia-e-
                # set-role.md, §2.3.3): chave AUSENTE (cliente antigo, ou
                # entrada que ja estava no outbox do IndexedDB antes do
                # deploy) != chave enviada com um valor. `payload.get(...)`
                # sozinho nao distingue os dois -- por isso o `in` explicito.
                # A checagem fica na VIEW, nunca em record_load: o servico
                # so recebe o valor ja resolvido, sem aplicar default por
                # conta propria (fecha a janela em que uma entrada
                # pendente da UI antiga seria confundida com uma escolha
                # real de "serie principal" depois do deploy).
                if 'set_role' in payload:
                    set_role_kwargs = {'set_role': payload.get('set_role')}
                else:
                    set_role_kwargs = {'set_role': PublicWorkoutLoadLogSetRole.LEGACY_UNKNOWN}
                result = record_load(
                    account_id=account_id,
                    movement_slug=movement_slug,
                    weight_kg=_decimal_or_none(payload.get('weight_kg')),
                    reps=_reps_or_none(payload.get('reps')),
                    rir=_decimal_or_none(payload.get('rir')),
                    performed_on=performed_on,
                    program_id=payload.get('program_id'),
                    week_in_program=payload.get('week_in_program'),
                    idempotency_key=idempotency_key,
                    **set_role_kwargs,
                )
        except LoadCorrectionConflictError as exc:
            current = active_correction_successor(
                account_id=account_id, supersedes_idempotency_key=supersedes_key,
            )
            return JsonResponse({'error': str(exc), 'active_record': current}, status=409)
        except (LoadValueError, LoadCorrectionNotFoundError, ValueError) as exc:
            return JsonResponse({'error': str(exc)}, status=400)

        return JsonResponse(result, status=200)


class PublicWorkoutRecordAssessmentView(View):
    """POST /renan/<slug>/avaliacoes — autoavaliacao fisica ONLINE. US Navy
    (so fita metrica) sempre disponivel; dobras cutaneas Jackson-Pollock
    7 pontos quando liberado (ver `skinfolds` abaixo). Onda A3/B4 do
    CORDA. Contrapartida de ESCRITA de PublicWorkoutAssessmentsView
    (GET .../avaliacoes.json, so leitura).

    PONTOS CRITICOS:
    - Mesma regra de auth de PublicWorkoutRecordLoadView: exige sessao de
      LOGIN ativa (401 sem sessao) e gate de posse do slug (404, nunca 403).
      Na consultoria ONLINE, e o proprio aluno que mede e lanca — decisao
      confirmada com o Renan.
    - `body_fat_percent`/`body_fat_source` NUNCA vem direto do aluno, nem
      quando manda dobras: sao SEMPRE calculados aqui a partir de dado
      cru (`measurements` pra US Navy — na verdade em build_report, em
      tempo de leitura; `age`+`skinfolds` pra Jackson-Pollock, aqui, em
      tempo de escrita, porque a idade nao e persistida em lugar nenhum
      pra poder recalcular depois — mesmo padrao do --age do management
      command). Pedido que traga qualquer um dos dois direto e' 400.
    - `skinfolds` (7 dobras em mm: peitoral/axilar/triceps/subescapular/
      abdomen/iliaca/coxa — mesmos nomes do management command) so e'
      aceito quando `has_presencial_skinfold_assessment` confirma que o
      treinador ja lancou pelo menos 1 avaliacao por dobra deste plano
      presencialmente (decisao do Renan: so confia na tecnica do aluno
      pinçando a dobra sozinho depois de ele ja ter sido calibrado ao
      vivo). Revalidado aqui a cada request — o `skinfold_self_report_unlocked`
      que avaliacoes.json devolve e' so pra tela decidir se MOSTRA a
      secao, nunca autorizacao de verdade.
    """

    _SKINFOLD_KEYS = ('peitoral', 'axilar', 'triceps', 'subescapular', 'abdomen', 'iliaca', 'coxa')

    def post(self, request, plan_slug, *args, **kwargs):
        plan = _get_public_workout_entry(plan_slug)

        from student_identity.public_workout_session import get_public_workout_account_id_from_request

        account_id = get_public_workout_account_id_from_request(request)
        if account_id is None:
            return JsonResponse({'error': 'login necessario'}, status=401)

        _confirm_login_session_owns_slug_or_404(request, plan.slug)

        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        except (json.JSONDecodeError, UnicodeDecodeError):
            return HttpResponse(status=400)
        if not isinstance(payload, dict):
            return HttpResponse(status=400)

        if 'body_fat_percent' in payload or 'body_fat_source' in payload:
            return JsonResponse(
                {'error': 'body_fat_percent/body_fat_source nunca vem direto do aluno — sao sempre calculados aqui'},
                status=400,
            )

        measured_at = payload.get('measured_at')
        weight_kg = payload.get('weight_kg')
        measurements = payload.get('measurements')
        skinfolds = payload.get('skinfolds')
        if not measured_at:
            return JsonResponse({'error': 'measured_at e obrigatorio'}, status=400)
        if measurements is not None and not isinstance(measurements, dict):
            return JsonResponse({'error': 'measurements deve ser um objeto'}, status=400)
        if skinfolds is not None and not isinstance(skinfolds, dict):
            return JsonResponse({'error': 'skinfolds deve ser um objeto'}, status=400)
        if not weight_kg and not measurements and not skinfolds:
            return JsonResponse({'error': 'informe weight_kg, measurements ou skinfolds'}, status=400)

        from public_workouts.services import (
            AssessmentValueError,
            has_presencial_skinfold_assessment,
            record_assessment,
            resolve_assessment_profile,
        )

        # Sexo/altura do aluno (catalogo ou ultima avaliacao presencial): vao
        # gravados nesta avaliacao tambem, pra o relatorio continuar completo.
        profile = resolve_assessment_profile(
            plan_slug=plan.slug, plan_sex=plan.assessment_sex, plan_height_cm=plan.height_cm
        )
        body_fat_kwargs = {}
        notes = payload.get('notes', '')
        if skinfolds is not None:
            if not has_presencial_skinfold_assessment(plan_slug=plan.slug):
                return JsonResponse(
                    {
                        'error': (
                            'dobras cutaneas ainda nao liberadas — '
                            'precisa de uma avaliacao presencial com o treinador primeiro'
                        )
                    },
                    status=403,
                )
            missing = [key for key in self._SKINFOLD_KEYS if key not in skinfolds]
            if missing:
                return JsonResponse({'error': f'faltam dobras: {", ".join(missing)}'}, status=400)
            if 'age' not in payload:
                return JsonResponse({'error': 'age e obrigatorio para lancar dobras cutaneas'}, status=400)

            try:
                fold_values = {key: float(skinfolds[key]) for key in self._SKINFOLD_KEYS}
                age_value = float(payload.get('age'))
            except (TypeError, ValueError):
                return JsonResponse({'error': 'age e as dobras precisam ser numeros'}, status=400)
            if age_value <= 0 or any(v <= 0 for v in fold_values.values()):
                return JsonResponse({'error': 'age e as dobras devem ser numeros positivos'}, status=400)
            # A formula muda com o sexo; antes caia na masculina sem avisar.
            # A avaliacao presencial (que libera esta secao) registra o sexo.
            if not profile['sex']:
                return JsonResponse(
                    {
                        'error': (
                            'sexo ainda nao registrado — peca ao treinador para completar '
                            'sua avaliacao presencial antes de lancar dobras'
                        )
                    },
                    status=409,
                )

            from public_workouts.formulas import estimate_body_fat_jackson_pollock_7site

            computed_bf = estimate_body_fat_jackson_pollock_7site(
                sex=profile['sex'],
                age=age_value,
                chest_mm=fold_values['peitoral'],
                midaxillary_mm=fold_values['axilar'],
                triceps_mm=fold_values['triceps'],
                subscapular_mm=fold_values['subescapular'],
                abdomen_mm=fold_values['abdomen'],
                suprailiac_mm=fold_values['iliaca'],
                thigh_mm=fold_values['coxa'],
            )
            if computed_bf is None:
                return JsonResponse(
                    {'error': 'nao foi possivel calcular o %gordura com essas medidas — confira os valores'},
                    status=400,
                )
            body_fat_kwargs = {'body_fat_percent': computed_bf, 'body_fat_source': 'skinfold_jp7'}
            skinfold_note = 'Dobras (mm): ' + ', '.join(f'{key}={fold_values[key]:g}' for key in self._SKINFOLD_KEYS)
            notes = f'{notes} {skinfold_note}'.strip()

        try:
            result = record_assessment(
                plan_slug=plan.slug,
                measured_at=measured_at,
                weight_kg=_decimal_or_none(weight_kg),
                measurements=measurements,
                notes=notes,
                sex=profile['sex'] or '',
                height_cm=profile['height_cm'],
                **body_fat_kwargs,
            )
        except (AssessmentValueError, ValueError) as exc:
            return JsonResponse({'error': str(exc)}, status=400)

        return JsonResponse(result, status=200)


class PublicWorkoutDownloadPdfView(View):
    """GET /renan/<slug>/treino.pdf — baixa o programa ativo em PDF
    (`public_workouts.pdf_export.render_program_pdf`, Entrega 4.6).

    PONTOS CRITICOS:
    - Mesma regra de auth da propria pagina/`avaliacoes.json`: cookie de
      posse do B0 (`get_public_workout_owner_slug`), 404 sem cookie ou com
      cookie de outro slug, nunca 403 (403 confirmaria que o slug existe).
      Nao exige login (B1) — baixar em PDF o MESMO conteudo que
      `/renan/<slug>` ja mostra na tela nao e' operacao de conta, e' so
      outro formato de saida pro que quem abriu o link ja pode ver.
    - 404 tambem quando ainda nao ha programa publicado
      (`get_active_program` devolve None) — vale pra todos os 10 slugs
      reais hoje, ate a Onda A2 migrar os programas de verdade. Mesmo
      raciocinio dos outros 404 desta view: nunca inventa pagina especial,
      so nao tem o que servir ainda.
    """

    def get(self, request, plan_slug, *args, **kwargs):
        plan = _get_public_workout_entry(plan_slug)
        _confirm_subscription_active_or_404(plan.slug)
        if get_public_workout_owner_slug(request) != plan.slug:
            raise Http404('Treino publico nao encontrado.')

        from public_workouts.services import get_active_program

        payload = get_active_program(slug=plan.slug)
        if payload is None:
            raise Http404('PDF ainda nao disponivel para este treino.')

        from public_workouts.pdf_export import render_program_pdf

        pdf_bytes = render_program_pdf(payload)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="treino-{plan.slug}.pdf"'
        return response
