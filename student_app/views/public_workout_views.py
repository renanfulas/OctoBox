"""
ARQUIVO: corredor publico de treinos em modo PWA.

POR QUE ELE EXISTE:
- separa os links publicos sem login da fronteira autenticada do app do aluno.

O QUE ESTE ARQUIVO FAZ:
1. entrega paginas HTML publicas dos treinos compartilhados.
2. publica manifest, service worker e fallback offline do PWA publico.

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
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.views.generic import View

from .base import (
    STUDENT_APP_APPLE_TOUCH_ICON,
    STUDENT_APP_ICON_192,
    STUDENT_APP_ICON_512,
    STUDENT_APP_ICON_MASKABLE_512,
)


PUBLIC_WORKOUT_SCOPE = '/renan/'
PUBLIC_WORKOUT_OFFLINE_URL = '/renan/offline/'

# B0 (CORDA docs/plans/public-workouts-produtizacao-corda.md) — cookie
# assinado que prova posse do link, nao identidade de verdade (isso so
# chega na Onda B1, com PublicWorkoutAccount). Setado por
# PublicWorkoutDetailView na primeira visita a /renan/<slug>; conferido por
# PublicWorkoutAssessmentsView antes de devolver dado de saude. Sem cookie,
# ou cookie de outro slug: 404, nunca 403 (403 confirmaria que o slug existe).
PUBLIC_WORKOUT_OWNER_COOKIE = 'renan_slug'
PUBLIC_WORKOUT_OWNER_COOKIE_SALT = 'public_workouts.owner_slug'
PUBLIC_WORKOUT_OWNER_COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1 ano

# R1 do CORDA: corrigir o codigo do A4 nao apaga as copias ja gravadas nos
# aparelhos com PWA instalado. So um VERSION novo expurga. Bump manual e
# deliberado — nao depende do mtime dos assets estaticos, que nao mudam
# nesta correcao. Bumpar de novo sempre que uma correcao de seguranca
# precisar forcar a troca de cache em todos os aparelhos.
PUBLIC_WORKOUT_CACHE_EPOCH = 2
PUBLIC_WORKOUT_ICON_192 = STUDENT_APP_ICON_192
PUBLIC_WORKOUT_ICON_512 = STUDENT_APP_ICON_512
PUBLIC_WORKOUT_ICON_MASKABLE_512 = STUDENT_APP_ICON_MASKABLE_512
PUBLIC_WORKOUT_APPLE_TOUCH_ICON = STUDENT_APP_APPLE_TOUCH_ICON

# Assets estaticos que o service worker pre-carrega no install.
# Caminhos SEM hash de proposito: o ManifestStaticFilesStorage mantem o
# arquivo original ao lado do hasheado, e o PWA de /aluno/ ja depende disso
# em producao (ver pwa_views.py).
# CUIDADO: cache.addAll() rejeita o install INTEIRO se um item der 404 —
# uma entrada errada aqui mata o modo offline de todos os alunos.
PUBLIC_WORKOUT_STATIC_ASSETS: tuple[str, ...] = (
    PUBLIC_WORKOUT_ICON_192,
    PUBLIC_WORKOUT_ICON_512,
    PUBLIC_WORKOUT_ICON_MASKABLE_512,
    PUBLIC_WORKOUT_APPLE_TOUCH_ICON,
    '/static/images/student-app-icon.svg',
)


@dataclass(frozen=True)
class PublicWorkoutAccent:
    """Rampa de accent do aluno — o UNICO eixo legitimo de branding.

    Todo o resto dos tokens (neutros, raio, sombra, badges de serie) e
    compartilhado. Os arquivos divergem no NOME da familia (--accent nos
    5 modernos, --amber na milene, --blue na giovanna) mas nao no papel.
    """

    base: str
    bg: str
    border: str
    light: str
    dark: str


@dataclass(frozen=True)
class PublicWorkoutPlan:
    """Configuracao de um treino publico.

    CONGELADO — mexer aqui causa dano silencioso:
    - `slug` esta em links ja distribuidos aos alunos (ver public_urls.py).
    - `store_key` e o namespace do localStorage: trocar apaga o historico
      de carga que o aluno digitou, sem aviso e sem backup.
    - `title` alimenta o manifest e `short_name` e derivado dele.
    """

    slug: str
    title: str
    theme_color: str
    background_color: str
    template_file: str
    accent: PublicWorkoutAccent
    tabs: tuple[tuple[str, str], ...]
    tracker_weeks: int = 0
    store_key: str | None = None
    # Constantes do aluno usadas pela aba Avaliacoes (public_workouts app)
    # para estimar %gordura (formula US Navy) e classificar RCQ — nao mudam
    # entre avaliacoes, por isso vivem na config do plano, nao no banco.
    # None desativa BF%/RCQ no relatorio (so IMC e circunferencias aparecem).
    assessment_sex: str | None = None
    height_cm: float | None = None

    @property
    def short_name(self) -> str:
        # Derivacao preservada: o teste do manifest assere 'Juliana'.
        return self.title.replace('Treino ', '')[:12]

    @property
    def manifest_url(self) -> str:
        return f'/renan/{self.slug}/manifest.webmanifest'


_TAB_TREINO = ('treino', 'Treinos')
_TAB_CARDIO = ('cardio', 'Cardio')
_TAB_PERIOD = ('period', 'Periodização')
_TAB_AVALIACOES = ('avaliacoes', 'Avaliações')

PUBLIC_WORKOUT_LIBRARY: dict[str, PublicWorkoutPlan] = {
    plan.slug: plan
    for plan in (
        PublicWorkoutPlan(
            slug='juliana',
            title='Treino Juliana',
            theme_color='#0f172a',
            background_color='#f5efe4',
            template_file='juliana.html',
            accent=PublicWorkoutAccent('#E11D48', '#FFF1F2', '#FECDD3', '#FBD7DF', '#BE123C'),
            tabs=(_TAB_TREINO, _TAB_CARDIO, _TAB_PERIOD, _TAB_AVALIACOES),
            tracker_weeks=5,
            store_key='juliana_alves_v3',  # gitleaks:allow — namespace de localStorage, nao segredo
        ),
        PublicWorkoutPlan(
            slug='bruno',
            title='Treino Bruno',
            theme_color='#11203b',
            background_color='#f4efe6',
            template_file='bruno.html',
            accent=PublicWorkoutAccent('#EA580C', '#FFF7ED', '#FED7AA', '#FFEDD5', '#C2410C'),
            tabs=(_TAB_TREINO, _TAB_CARDIO, ('nutri', 'Nutrição'), _TAB_PERIOD, _TAB_AVALIACOES),
            tracker_weeks=5,
            store_key='bruno_cutting_v1',  # gitleaks:allow — namespace de localStorage, nao segredo
        ),
        PublicWorkoutPlan(
            slug='milene',
            title='Treino Milene',
            theme_color='#1a1a1a',
            background_color='#fafaf7',
            template_file='milene.html',
            accent=PublicWorkoutAccent('#D97706', '#FFFBEB', '#FDE68A', '#FEF3C7', '#92400E'),
            tabs=(_TAB_TREINO, _TAB_PERIOD, _TAB_AVALIACOES),
            tracker_weeks=5,
            store_key='milene_geraldes_treino',  # gitleaks:allow — namespace de localStorage, nao segredo
        ),
        PublicWorkoutPlan(
            slug='giovanna',
            title='Treino Giovanna',
            theme_color='#172017',
            background_color='#f8faf7',
            template_file='giovanna.html',
            # A giovanna so declara 3 degraus (--blue/-bg/-border), e sao os
            # mesmos valores do henrique. Os dois faltantes vem dele.
            accent=PublicWorkoutAccent('#2563EB', '#EFF6FF', '#BFDBFE', '#DBEAFE', '#1D4ED8'),
            tabs=(_TAB_TREINO, _TAB_PERIOD, _TAB_AVALIACOES),
            tracker_weeks=5,
            # store_key novo: esta pagina nunca teve tracker, entao nao ha
            # historico anterior para preservar.
            store_key='giovanna_fontes_v1',  # gitleaks:allow — namespace de localStorage, nao segredo
        ),
        PublicWorkoutPlan(
            slug='thaislima',
            title='Treino Thais Lima',
            theme_color='#111111',
            background_color='#f6f5f2',
            template_file='thaislima.html',
            accent=PublicWorkoutAccent('#7C3AED', '#F5F3FF', '#DDD6FE', '#EDE9FE', '#5B21B6'),
            tabs=(_TAB_TREINO, _TAB_CARDIO, _TAB_AVALIACOES),
            tracker_weeks=5,
            store_key='thais_lima_v1',  # gitleaks:allow — namespace de localStorage, nao segredo
        ),
        PublicWorkoutPlan(
            slug='john',
            title='Treino John',
            theme_color='#111111',
            background_color='#f6f5f2',
            template_file='john.html',
            accent=PublicWorkoutAccent('#0891B2', '#ECFEFF', '#A5F3FC', '#CFFAFE', '#0E7490'),
            tabs=(_TAB_TREINO, _TAB_PERIOD, _TAB_AVALIACOES),
            tracker_weeks=6,  # unico plano com mesociclo de 6 semanas
            store_key='john_v1',  # gitleaks:allow — namespace de localStorage, nao segredo
        ),
        PublicWorkoutPlan(
            slug='henrique',
            title='Treino Henrique',
            theme_color='#141414',
            background_color='#f6f5f2',
            template_file='henrique.html',
            accent=PublicWorkoutAccent('#2563EB', '#EFF6FF', '#BFDBFE', '#DBEAFE', '#1D4ED8'),
            tabs=(_TAB_TREINO, _TAB_CARDIO, _TAB_PERIOD, _TAB_AVALIACOES),
            tracker_weeks=5,
            store_key='henrique_santos_souza_v1',  # gitleaks:allow — namespace de localStorage, nao segredo
        ),
        PublicWorkoutPlan(
            slug='johnespanha',
            title='Treino John Espanha',
            theme_color='#141414',
            background_color='#fdf2f8',
            template_file='johnespanha.html',
            accent=PublicWorkoutAccent('#DB2777', '#FDF2F8', '#FBCFE8', '#FCE7F3', '#BE185D'),
            tabs=(_TAB_TREINO, _TAB_CARDIO, _TAB_AVALIACOES),
            tracker_weeks=5,
            store_key='john_espanha_v1',  # gitleaks:allow — namespace de localStorage, nao segredo
            # NAO convertido para o design system compartilhado: chegou em
            # main (PR #170/#171) depois desta refatoracao, ainda no formato
            # monolitico antigo (CSS/JS proprios embutidos no arquivo). Os
            # campos acima entram na PUBLIC_WORKOUT_LIBRARY so para manter o
            # manifest/service-worker corretos; renderiza como pagina
            # autocontida, igual os outros 7 rendiam antes desta PR.
        ),
        PublicWorkoutPlan(
            slug='franciele',
            title='Treino Franciele',
            theme_color='#241b2e',
            background_color='#faf6f3',
            template_file='franciele.html',
            accent=PublicWorkoutAccent('#A21CAF', '#FDF4FF', '#F5D0FE', '#FAE8FF', '#86198F'),
            tabs=(_TAB_TREINO, _TAB_PERIOD, _TAB_AVALIACOES),
            tracker_weeks=4,
            store_key='franciele_v1',  # gitleaks:allow — namespace de localStorage, nao segredo
            assessment_sex='F',
            height_cm=173,
        ),
        PublicWorkoutPlan(
            slug='rafael',
            title='Treino Rafael',
            theme_color='#0e2933',
            background_color='#f4fbfc',
            template_file='rafael.html',
            accent=PublicWorkoutAccent('#0891B2', '#ECFEFF', '#A5F3FC', '#CFFAFE', '#0E7490'),
            tabs=(_TAB_TREINO, _TAB_PERIOD, _TAB_AVALIACOES),
            tracker_weeks=4,
            store_key='rafael_v1',  # gitleaks:allow — namespace de localStorage, nao segredo
            assessment_sex='M',
            height_cm=175,
        ),
    )
}


# Ordem importa: tokens antes de tudo, mobile por ultimo (sobrescreve).
# Estes MESMOS caminhos vao para o ALLOWLIST do service worker, entao
# precisam ser planos (sem {% static %}): o allowlist nao sabe resolver
# nome hasheado do ManifestStaticFilesStorage.
PUBLIC_WORKOUT_STYLESHEETS: tuple[str, ...] = (
    '/static/css/public_workouts/tokens.css',
    '/static/css/public_workouts/layout.css',
    '/static/css/public_workouts/components.css',
    '/static/css/public_workouts/tracker.css',
    '/static/css/public_workouts/period.css',
    '/static/css/public_workouts/install-prompt.css',
    '/static/css/public_workouts/assessments.css',
    '/static/css/public_workouts/mobile.css',
)

PUBLIC_WORKOUT_SCRIPTS: tuple[str, ...] = (
    '/static/js/public_workouts/app.js',
    '/static/js/public_workouts/assessments.js',
)

_ASSET_VERSION_CACHE: dict[str, str] = {}


def public_workout_asset_version() -> str:
    """Versao usada no ?v= dos assets e no nome do cache do service worker.

    ATENCAO: `STATIC_ASSET_VERSION` esta SEMPRE definida em settings, com
    valor '1' quando o ambiente nao seta nada — e nenhum deploy seta
    (`RENDER_GIT_COMMIT` era do Render, e o projeto migrou para VPS). Ou
    seja: na producao de hoje o ?v= fica congelado em 1 para sempre, o
    cache do navegador nunca invalida e o service worker nunca troca de
    versao. Enquanto o CSS era inline isso nao aparecia, porque o estilo
    chegava junto com o HTML. Agora que e arquivo externo, apareceria.

    Quando o ambiente define a variavel de verdade, respeitamos. Caso
    contrario caimos no mtime dos proprios assets, que muda sozinho a
    cada deploy que altere um arquivo.
    """
    configured = getattr(settings, 'STATIC_ASSET_VERSION', '1')
    if configured and configured != '1':
        return configured

    if 'value' in _ASSET_VERSION_CACHE and not settings.DEBUG:
        return _ASSET_VERSION_CACHE['value']

    base_dir = Path(settings.BASE_DIR)
    mtimes = []
    for url in PUBLIC_WORKOUT_STYLESHEETS + PUBLIC_WORKOUT_SCRIPTS:
        path = base_dir / url.lstrip('/')
        if path.exists():
            mtimes.append(int(path.stat().st_mtime))
    version = str(max(mtimes, default=1))
    _ASSET_VERSION_CACHE['value'] = version
    return version


def _get_public_workout_entry(plan_slug: str) -> PublicWorkoutPlan:
    normalized_slug = (plan_slug or '').strip().lower()
    plan = PUBLIC_WORKOUT_LIBRARY.get(normalized_slug)
    if plan is None:
        raise Http404('Treino publico nao encontrado.')
    return plan


def _confirm_login_session_owns_slug_or_404(request, plan_slug: str) -> None:
    """B3 (CORDA) item 5 — "identidade da sessao dona do slug, senao 404".

    So entra em jogo quando ha sessao de LOGIN ativa (PublicWorkoutAccount,
    Onda B1) — visitante anonimo continua no fluxo B0 de posse por cookie,
    sem mudanca (fase B de login obrigatorio ainda nao esta ligada, Onda
    B3 fases B/C). Com sessao ativa: aluno A logado abrindo o slug do
    aluno B tem que receber 404, nunca o treino nem 403 (403 confirmaria
    que o slug existe — mesma regra do cookie de posse do B0).

    Import tardio (nao no topo do arquivo): mesmo motivo de
    _validate_plan_slug em public_workouts/services.py — este modulo e
    importado por public_workouts (PUBLIC_WORKOUT_LIBRARY), um import de
    public_workouts aqui no topo criaria ciclo.
    """
    from public_workouts.models import PublicWorkoutSubscription
    from student_identity.public_workout_session import get_public_workout_account_id_from_request

    account_id = get_public_workout_account_id_from_request(request)
    if account_id is None:
        return

    owns_slug = PublicWorkoutSubscription.objects.filter(account_id=account_id, plan_slug=plan_slug).exists()
    if not owns_slug:
        raise Http404('Treino publico nao encontrado.')


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


# Presente em qualquer pagina que estenda public_workouts/_base.html —
# usado para distinguir template convertido de arquivo legado (ver baixo).
_SHARED_BASE_MARKER = 'id="public-workout-install"'

_LEGACY_VIEWPORT_MARKERS = (
    '<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">',
    '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
)

_LEGACY_INSTALL_PROMPT_MARKUP = """
<style>
.public-workout-install{
  position:fixed;
  right:16px;
  bottom:16px;
  z-index:9999;
  display:none;
  align-items:center;
  gap:10px;
  max-width:min(320px,calc(100vw - 32px));
  padding:12px 14px;
  border-radius:18px;
  background:rgba(17,32,59,.94);
  color:#fff;
  box-shadow:0 16px 34px rgba(15,23,42,.28);
  font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
}
.public-workout-install.is-visible{display:flex}
.public-workout-install__copy{font-size:13px;line-height:1.35}
.public-workout-install__button{
  border:0;
  border-radius:999px;
  padding:10px 14px;
  background:#f5efe4;
  color:#11203b;
  font-weight:700;
  font-size:13px;
  cursor:pointer;
  white-space:nowrap;
}
@media (max-width: 640px){
  .public-workout-install{
    left:12px;
    right:12px;
    bottom:12px;
    max-width:none;
  }
}
</style>
<div class="public-workout-install" id="public-workout-install" aria-live="polite">
  <div class="public-workout-install__copy" id="public-workout-install-copy"></div>
  <button class="public-workout-install__button" id="public-workout-install-button" type="button"></button>
</div>
""".strip()

_LEGACY_SW_REGISTRATION_SCRIPT = """
<script>
(function () {
  var installPrompt = null;
  var installRoot = document.getElementById('public-workout-install');
  var installCopy = document.getElementById('public-workout-install-copy');
  var installButton = document.getElementById('public-workout-install-button');
  var isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
  var isIos = /iphone|ipad|ipod/i.test(window.navigator.userAgent);

  function showInstall(copy, buttonLabel, onClick) {
    if (!installRoot || !installCopy || !installButton || isStandalone) {
      return;
    }
    installCopy.textContent = copy;
    installButton.textContent = buttonLabel;
    installButton.onclick = onClick;
    installRoot.classList.add('is-visible');
  }

  if (!('serviceWorker' in navigator)) {
    if (isIos) {
      showInstall('No iPhone/iPad, toque em Compartilhar e depois em Adicionar \\u00e0 Tela de In\\u00edcio.', 'Entendi', function () {
        installRoot.classList.remove('is-visible');
      });
    }
    return;
  }

  if (isIos) {
    showInstall('No iPhone/iPad, toque em Compartilhar e depois em Adicionar \\u00e0 Tela de In\\u00edcio.', 'Entendi', function () {
      installRoot.classList.remove('is-visible');
    });
  }

  window.addEventListener('beforeinstallprompt', function (event) {
    event.preventDefault();
    installPrompt = event;
    showInstall('Instale este treino na tela inicial para abrir como app, sem login.', 'Instalar app', function () {
      if (!installPrompt) {
        return;
      }
      installPrompt.prompt();
      installPrompt.userChoice.finally(function () {
        installPrompt = null;
        installRoot.classList.remove('is-visible');
      });
    });
  });

  window.addEventListener('appinstalled', function () {
    if (installRoot) {
      installRoot.classList.remove('is-visible');
    }
  });

  window.addEventListener('load', function () {
    var ownSlug = (document.body.getAttribute('data-plan-slug') || '');
    navigator.serviceWorker
      .register('/renan/sw.js?slug=' + encodeURIComponent(ownSlug), { scope: '/renan/' })
      .catch(function () {
        // O treino continua abrindo mesmo sem o service worker.
      });
  });
})();
</script>
""".strip()


def _inject_legacy_pwa_head(html: str, plan: PublicWorkoutPlan, asset_version: str) -> str:
    """Injeta manifest/instalacao/service-worker em arquivo NAO convertido.

    E o mecanismo original (substituicao de string), mantido vivo so para
    templates que ainda nao viraram `{% extends '_base.html' %}` — hoje,
    rafael/franciele/johnespanha, que chegaram em PRs paralelos enquanto
    aquela refatoracao estava em andamento. Qualquer novo arquivo nesse
    formato continua funcionando ate ser convertido.

    Tambem injeta CSS/JS da aba Avaliacoes (public_workouts app): arquivos
    legados nao consomem `stylesheet_urls`/`app.js` do design system
    compartilhado (nao tem `{% for %}` nenhum, sao HTML cru), entao esses
    dois assets especificos precisam de link/script proprios aqui — e
    `data-plan-slug` no <body>, que e como assessments.js descobre qual
    plano buscar em /renan/<slug>/avaliacoes.json.
    """
    head_injection = (
        f'<meta name="theme-color" content="{plan.theme_color}">\n'
        '<meta name="mobile-web-app-capable" content="yes">\n'
        '<meta name="apple-mobile-web-app-capable" content="yes">\n'
        '<meta name="apple-mobile-web-app-status-bar-style" content="default">\n'
        f'<meta name="apple-mobile-web-app-title" content="{plan.title}">\n'
        f'<link rel="manifest" href="{plan.manifest_url}">\n'
        f'<link rel="apple-touch-icon" href="{PUBLIC_WORKOUT_APPLE_TOUCH_ICON}">\n'
        '<link rel="icon" href="/static/images/student-app-icon.svg" type="image/svg+xml">\n'
        f'<link rel="icon" href="{PUBLIC_WORKOUT_ICON_192}" sizes="192x192" type="image/png">\n'
        f'<link rel="stylesheet" href="/static/css/public_workouts/assessments.css?v={asset_version}">'
    )
    for marker in _LEGACY_VIEWPORT_MARKERS:
        if marker in html:
            html = html.replace(marker, f'{marker}\n{head_injection}', 1)
            break

    if 'data-plan-slug=' not in html:
        html = html.replace('<body>', f'<body data-plan-slug="{plan.slug}">', 1)

    if "navigator.serviceWorker.register('/renan/sw.js'" not in html:
        html = html.replace(
            '</body>',
            f'{_LEGACY_INSTALL_PROMPT_MARKUP}\n{_LEGACY_SW_REGISTRATION_SCRIPT}\n</body>',
            1,
        )

    if 'assessments.js' not in html:
        html = html.replace(
            '</body>',
            f'<script src="/static/js/public_workouts/assessments.js?v={asset_version}"></script>\n</body>',
            1,
        )
    return html


def _render_public_workout_html(plan_slug: str) -> str:
    """Renderiza a pagina do plano a partir do template do aluno.

    O <head>, o prompt de instalacao e o registro do service worker vem
    de public_workouts/_base.html PARA TEMPLATES CONVERTIDOS. Arquivos
    ainda nao convertidos (ver `_inject_legacy_pwa_head`) continuam
    recebendo isso por substituicao de string, como era antes.

    render_to_string SEM request de proposito: render(request, ...)
    dispararia access.context_processors.role_navigation, que consulta o
    banco com usuario anonimo no schema public. Ver pwa_views.py.
    """
    plan = _get_public_workout_entry(plan_slug)
    asset_version = public_workout_asset_version()
    try:
        html = render_to_string(
            f'public_workouts/{plan.template_file}',
            {
                'plan': plan,
                'stylesheet_urls': PUBLIC_WORKOUT_STYLESHEETS,
                'static_asset_version': asset_version,
                'apple_touch_icon': PUBLIC_WORKOUT_APPLE_TOUCH_ICON,
                'icon_192': PUBLIC_WORKOUT_ICON_192,
            },
        )
    except TemplateDoesNotExist:
        raise Http404('Arquivo de treino publico indisponivel.')

    if _SHARED_BASE_MARKER not in html:
        html = _inject_legacy_pwa_head(html, plan, asset_version)
    return html


class PublicWorkoutDetailView(View):
    def get(self, request, plan_slug, *args, **kwargs):
        plan = _get_public_workout_entry(plan_slug)
        _confirm_login_session_owns_slug_or_404(request, plan.slug)
        # get_token() marca o cookie CSRF pra ser enviado na resposta —
        # sem isso, o cookie nunca nasce aqui (nenhum template desta pagina
        # usa {% csrf_token %}) e o JS de escrita (autoavaliacao online,
        # assessments.js) nunca teria um X-CSRFToken valido pra mandar no
        # POST de /avaliacoes: 403 sempre, em qualquer navegador de verdade.
        from django.middleware.csrf import get_token

        get_token(request)
        response = HttpResponse(_render_public_workout_html(plan_slug))
        # B0: quem abre a pagina prova posse do link — e o que autoriza a
        # leitura de /avaliacoes.json a seguir. Cookie por instancia, nao
        # global: cada slug so autoriza a si mesmo.
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


class PublicWorkoutManifestView(View):
    def get(self, request, plan_slug, *args, **kwargs):
        entry = _get_public_workout_entry(plan_slug)
        manifest = {
            'id': f'/renan/{entry.slug}',
            'name': entry.title,
            'short_name': entry.short_name,
            'description': f'{entry.title} no formato rapido do OctoBox.',
            'start_url': f'/renan/{entry.slug}?source=pwa',
            'scope': PUBLIC_WORKOUT_SCOPE,
            'display': 'standalone',
            'orientation': 'portrait',
            'background_color': entry.background_color,
            'theme_color': entry.theme_color,
            'icons': [
                {
                    'src': PUBLIC_WORKOUT_ICON_192,
                    'sizes': '192x192',
                    'type': 'image/png',
                    'purpose': 'any',
                },
                {
                    'src': PUBLIC_WORKOUT_ICON_512,
                    'sizes': '512x512',
                    'type': 'image/png',
                    'purpose': 'any',
                },
                {
                    'src': PUBLIC_WORKOUT_ICON_MASKABLE_512,
                    'sizes': '512x512',
                    'type': 'image/png',
                    'purpose': 'maskable',
                },
            ],
        }
        return HttpResponse(json.dumps(manifest), content_type='application/manifest+json')


class PublicWorkoutServiceWorkerView(View):
    def get(self, request, *args, **kwargs):
        # A4 do CORDA: o precache nao pode mais trazer TODOS os slugs (isso
        # e o que faz o aparelho de um aluno guardar o dado de outro,
        # offline). Resolve em runtime, a partir do slug que a propria
        # pagina registrante informa via ?slug= (ver data-plan-slug em
        # _base.html e no head legado). Slug ausente ou desconhecido: SW
        # generico, sem nenhuma pagina de plano no precache.
        requested_slug = (request.GET.get('slug') or '').strip().lower()
        plan_slugs = (requested_slug,) if requested_slug in PUBLIC_WORKOUT_LIBRARY else ()
        js = render_to_string(
            'public_workouts/sw.js',
            {
                'asset_version': public_workout_asset_version(),
                'cache_epoch': PUBLIC_WORKOUT_CACHE_EPOCH,
                'offline_url': PUBLIC_WORKOUT_OFFLINE_URL,
                'app_scope': PUBLIC_WORKOUT_SCOPE,
                'plan_slugs': plan_slugs,
                # CSS e JS compartilhados entram no precache: sem eles a
                # pagina abre offline sem estilo e sem tracker.
                'static_asset_urls': (
                    PUBLIC_WORKOUT_STYLESHEETS
                    + PUBLIC_WORKOUT_SCRIPTS
                    + PUBLIC_WORKOUT_STATIC_ASSETS
                ),
            },
        )
        response = HttpResponse(js, content_type='application/javascript')
        response['Service-Worker-Allowed'] = PUBLIC_WORKOUT_SCOPE
        return response


class PublicWorkoutOfflineView(View):
    def get(self, request, *args, **kwargs):
        # A lista de alunos sai da biblioteca, nao de copy fixa: a versao
        # anterior citava so 4 nomes e linkava /renan/juliana, entao quem
        # entrou depois (thaislima, john, henrique) ficava de fora.
        html = render_to_string(
            'public_workouts/offline.html',
            {'plans': tuple(PUBLIC_WORKOUT_LIBRARY.values())},
        )
        return HttpResponse(html)


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
        from public_workouts.services import get_active_program, list_program_versions
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
            'plan_slug': plan.slug,
            'accent_variant': plan.assessment_sex,
            'program': program,
            'program_versions': list_program_versions(slug=plan.slug),
            'load_history': [],
            'one_rep_max_by_movement': {},
            'trends_by_movement': {},
            'student_name': student_name,
            'student_photo_url': student_photo_url,
            'customer_portal_url': None,
            'account_email': account_email,
        })
        return HttpResponse(html)


class PublicWorkoutSignOutView(View):
    """POST /renan/<slug>/sair — "Sair da conta" da tela Perfil (fundacao B3,
    pedido do Renan pra fechar o paralelo com o app do aluno).

    So apaga o cookie de posse (PUBLIC_WORKOUT_OWNER_COOKIE, B0) — o
    corredor ainda nao tem login de sessao (fases B/C da Onda B3), entao
    hoje isto e' groundwork visual/funcional pra quando essa fase ligar, nao
    uma barreira de acesso de verdade: quem voltar a abrir /renan/<slug>
    ganha o cookie de volta automaticamente (PublicWorkoutDetailView.get
    sempre re-seta), so os endpoints de leitura/escrita que dependem dele
    ficam temporariamente sem posse ate a proxima visita.
    """

    def post(self, request, plan_slug, *args, **kwargs):
        response = redirect('public-workout-offline')
        response.delete_cookie(PUBLIC_WORKOUT_OWNER_COOKIE, samesite='Lax')
        return response


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
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f'valor numerico invalido: {value!r}') from exc


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

        from public_workouts.services import LoadValueError, record_load

        try:
            result = record_load(
                account_id=account_id,
                movement_slug=movement_slug,
                weight_kg=_decimal_or_none(payload.get('weight_kg')),
                reps=payload.get('reps'),
                rir=_decimal_or_none(payload.get('rir')),
                performed_on=performed_on,
                program_id=payload.get('program_id'),
                week_in_program=payload.get('week_in_program'),
                idempotency_key=idempotency_key,
            )
        except (LoadValueError, ValueError) as exc:
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

        from public_workouts.services import AssessmentValueError, has_presencial_skinfold_assessment, record_assessment

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

            from public_workouts.formulas import Sex, estimate_body_fat_jackson_pollock_7site

            computed_bf = estimate_body_fat_jackson_pollock_7site(
                sex=plan.assessment_sex or Sex.MALE,
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
