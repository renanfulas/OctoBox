"""Catálogo ativo e regras de posse/acesso do corredor Curva."""

from __future__ import annotations

from django.http import Http404

from public_workouts.catalog import (
    PublicWorkoutAccent, PublicWorkoutPlan, PUBLIC_WORKOUT_LIBRARY,
    _TAB_TREINO, _TAB_AVALIACOES,
)


# B0 (CORDA docs/plans/public-workouts-produtizacao-corda.md) — cookie
# assinado que prova posse do link, nao identidade de verdade (isso so
# chega na Onda B1, com PublicWorkoutAccount). Setado por
# PublicWorkoutDetailView na primeira visita a /renan/<slug>; conferido por
# PublicWorkoutAssessmentsView antes de devolver dado de saude. Sem cookie,
# ou cookie de outro slug: 404, nunca 403 (403 confirmaria que o slug existe).
PUBLIC_WORKOUT_OWNER_COOKIE = 'renan_slug'
PUBLIC_WORKOUT_OWNER_COOKIE_SALT = 'public_workouts.owner_slug'
PUBLIC_WORKOUT_OWNER_COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1 ano


def _synthesize_public_workout_plan(slug: str) -> PublicWorkoutPlan | None:
    """Fallback pra slug que NAO esta em PUBLIC_WORKOUT_LIBRARY mas TEM
    PublicWorkoutProgram ativo publicado (ex.: aprovado via
    services.approve_and_publish_draft — pipeline de anamnese+IA). Sem
    isto, um aluno novo aprovado por esse fluxo cairia em 404 em
    /renan/<slug> ate alguem editar este dict a mao e fazer deploy — gap
    real ja' documentado em
    docs/plans/public-workouts-produtizacao-corda.md:155,158 ("trocar a
    fonte dos slugs de dict para query em PublicWorkoutProgram").

    So' sintetiza tema GENERICO (nunca uma das paletas artesanais dos 10
    clientes legados) — branding fino por aluno continua sendo trabalho
    editorial de quem, se/quando quiser, adicionar a entrada de verdade
    neste dict depois. `template_file` fica vazio de proposito: so' e' lido
    quando o slug esta' em `_legacy_template_slugs()` (kill switch por env
    var), que nunca contem um slug que nao veio deste dict primeiro — um
    slug sintetizado aqui sempre renderiza pelo template unico
    (workout.html), nunca pelo caminho legado.

    Retorna None (nunca levanta) quando nem o dict nem o banco conhecem o
    slug — `_get_public_workout_entry` decide o 404, esta funcao so'
    resolve a origem do dado."""
    from public_workouts.services import get_active_program

    if get_active_program(slug=slug) is None:
        return None

    return PublicWorkoutPlan(
        slug=slug,
        title=f'Treino {slug.capitalize()}',
        theme_color='#0f172a',
        background_color='#f5efe4',
        template_file='',
        accent=PublicWorkoutAccent('#2451C4', '#EAF0FD', '#BFDBFE', '#DBEAFE', '#1B3A96'),
        tabs=(_TAB_TREINO, _TAB_AVALIACOES),
        tracker_weeks=0,
        store_key=f'{slug}_v1',
    )


def _get_public_workout_entry(plan_slug: str) -> PublicWorkoutPlan:
    normalized_slug = (plan_slug or '').strip().lower()
    plan = PUBLIC_WORKOUT_LIBRARY.get(normalized_slug)
    if plan is None:
        # Query extra (indexada por slug) so' acontece pro caso ausente do
        # dict em memoria — custo aceito: corredor de baixo trafego, e o
        # caminho comum (slug real, nos 10 legados ou ja' sintetizado antes)
        # nunca chega aqui.
        plan = _synthesize_public_workout_plan(normalized_slug)
    if plan is None:
        raise Http404('Treino publico nao encontrado.')
    return plan


def _confirm_subscription_active_or_404(plan_slug: str) -> None:
    """P0 do acesso pago pro fluxo de cadastro a frio + Stripe (achado
    real: ate aqui NADA checava isto — uma assinatura SUSPENDED/PAST_DUE/
    CANCELED continuava vendo o treino inteiro).

    So' bloqueia quando EXISTE uma PublicWorkoutSubscription pra este slug
    E ela nao esta ACTIVE — nunca quando nao existe assinatura nenhuma.
    Isso e' deliberado, nao um buraco: os 10 clientes legados (seed_legacy_
    workout_accounts) "sao clientes pagantes reais hoje, so que fora do
    fluxo de checkout Stripe deste corredor" (docstring do proprio
    comando) — pagam o Renan por fora, nunca tiveram (nem deveriam ter)
    o acesso deles condicionado a um `PublicWorkoutSubscription.status`
    que o fluxo Stripe deste corredor nem administra pra eles. O gate so'
    se aplica a quem de fato passou pelo checkout Stripe (cadastro a frio
    ou assinatura de legado) e tem uma linha de assinatura pra checar.
    Nunca 404 vira 403 (mesma razao de sempre em todo este arquivo: 403
    confirmaria que a conta existe).

    Roda pra QUALQUER visita, com sessao de login ou so' com o cookie de
    posse B0 — chamada de dentro de _confirm_login_session_owns_slug_or_404
    (cobre a maioria dos endpoints) e direto por quem usa o cookie B0 em
    vez de sessao (PublicWorkoutDownloadPdfView).

    O modelo fica em import local para manter o carregamento desta politica
    leve; o catalogo estatico nao depende de ORM.
    """
    from public_workouts.models import PublicWorkoutSubscription, PublicWorkoutSubscriptionStatus

    subscription = PublicWorkoutSubscription.objects.filter(plan_slug=plan_slug).first()
    if subscription is not None and subscription.status != PublicWorkoutSubscriptionStatus.ACTIVE:
        raise Http404('Treino publico nao encontrado.')


def _confirm_ownership_or_404(request, plan_slug: str) -> None:
    """B3 (CORDA) item 5 — "identidade da sessao dona do slug, senao 404".

    So entra em jogo quando ha sessao de LOGIN ativa (PublicWorkoutAccount,
    Onda B1) — visitante anonimo continua no fluxo B0 de posse por cookie,
    sem mudanca (fase B de login obrigatorio ainda nao esta ligada, Onda
    B3 fases B/C). Com sessao ativa: aluno A logado abrindo o slug do
    aluno B tem que receber 404, nunca o treino nem 403 (403 confirmaria
    que o slug existe — mesma regra do cookie de posse do B0).

    Separada de _confirm_subscription_active_or_404 de proposito (achado
    real, feedback do Renan): posse errada continua 404 silencioso (nunca
    revela que o slug de OUTRA pessoa existe), mas pagamento pendente do
    PROPRIO dono nao devia ser silencioso — a pessoa que chega com o link
    certo E' o dono (mesma logica de posse-prova-identidade de sempre
    neste arquivo), entao PublicWorkoutDetailView mostra uma tela
    explicando o bloqueio e como resolver, em vez de 404 (ver mais abaixo).
    Os endpoints de API/sub-recurso continuam so' com
    _confirm_login_session_owns_slug_or_404 (404 direto, sem tela — nao
    fazem sentido pra visualizacao humana).

    O import dos modelos fica local para nao obrigar ORM no carregamento
    do catalogo e desta politica.
    """
    from public_workouts.models import PublicWorkoutSubscription
    from student_identity.public_workout_session import get_public_workout_account_id_from_request

    account_id = get_public_workout_account_id_from_request(request)
    if account_id is None:
        return

    owns_slug = PublicWorkoutSubscription.objects.filter(account_id=account_id, plan_slug=plan_slug).exists()
    if not owns_slug:
        raise Http404('Treino publico nao encontrado.')


def _confirm_login_session_owns_slug_or_404(request, plan_slug: str) -> None:
    """Combina as duas checagens acima (status ACTIVE + posse) pros
    endpoints de API/sub-recurso — 404 direto pras duas, sem tela (nao sao
    paginas que um humano le, ver docstring de _confirm_ownership_or_404).
    """
    _confirm_subscription_active_or_404(plan_slug)
    _confirm_ownership_or_404(request, plan_slug)


def get_public_workout_owner_slug(request) -> str | None:
    """Le o cookie de posse do B0 (ver PUBLIC_WORKOUT_OWNER_COOKIE acima).

    None se ausente ou com assinatura adulterada — nunca levanta. Usado
    por toda view que precisa confirmar "este navegador visitou este
    slug antes" (avaliacoes.json, upload de backup do localStorage).

    `get_signed_cookie` com `default=` ja absorve BadSignature/KeyError
    internamente (ver django.http.request.HttpRequest.get_signed_cookie) —
    nao precisa de try/except aqui, ele nunca levanta com default setado.
    """
    return request.get_signed_cookie(
        PUBLIC_WORKOUT_OWNER_COOKIE, salt=PUBLIC_WORKOUT_OWNER_COOKIE_SALT, default=None
    )


