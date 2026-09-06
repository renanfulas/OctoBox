"""
ARQUIVO: configuracao base compartilhada entre desenvolvimento, homologacao e producao.

POR QUE ELE EXISTE:
- Evita repetir a mesma base de apps, templates, idioma, login e middlewares em varios arquivos.

O QUE ESTE ARQUIVO FAZ:
1. Define utilitarios para leitura de variaveis de ambiente.
2. Configura apps, middlewares, templates e autenticacao.
3. Centraliza idioma, timezone, estaticos e defaults reutilizaveis.
4. Expone funcoes para montar banco e flags booleanas com seguranca.

PONTOS CRITICOS:
- Qualquer mudanca aqui se propaga para todos os ambientes.
- Os parsers de variaveis afetam segredo, hosts, banco e endurecimento de seguranca.
"""

import ipaddress
import os
import socket
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from config.env_loader import load_project_env
from shared_support.box_runtime import box_partitioned_key_function, build_box_cache_key_prefix

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ACTIVE_SETTINGS_MODULE = os.getenv('DJANGO_SETTINGS_MODULE', '').strip().lower()
LOCAL_POSTGRES_DATABASE_URL = 'postgresql://postgres:postgres@127.0.0.1:5433/octobox_control'

load_project_env(
    BASE_DIR,
    include_test_file=ACTIVE_SETTINGS_MODULE.endswith('.test') or bool(os.getenv('PYTEST_CURRENT_TEST')),
)


def env_bool(name, default=False):
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {'1', 'true', 'yes', 'on'}


def env_int(name, default=0):
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value.strip())
    except (TypeError, ValueError):
        return default


def env_float(name, default=0.0):
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return float(raw_value.strip())
    except (TypeError, ValueError):
        return default


def env_list(name, default=''):
    raw_value = os.getenv(name, default)
    return [item.strip() for item in raw_value.split(',') if item.strip()]


def env_str(name, default=''):
    return os.getenv(name, default).strip()


def env_list_alias(names, default=''):
    for name in names:
        raw_value = os.getenv(name)
        if raw_value is not None and raw_value.strip():
            return env_list(name)
    return env_list(names[0], default)


def build_https_trusted_origins(hosts):
    origins = []
    for host in hosts:
        normalized_host = host.strip()
        if not normalized_host:
            continue
        origins.append(f'https://{normalized_host}')
    return sorted(dict.fromkeys(origins))


def merge_public_host_contract(allowed_hosts, trusted_origins, extra_hosts=()):
    merged_hosts = [host.strip() for host in allowed_hosts if host and host.strip()]
    merged_origins = [origin.strip().rstrip('/') for origin in trusted_origins if origin and origin.strip()]

    for host in extra_hosts:
        normalized_host = host.strip()
        if not normalized_host:
            continue
        merged_hosts.append(normalized_host)
        merged_origins.append(f'https://{normalized_host}')

    return sorted(dict.fromkeys(merged_hosts)), sorted(dict.fromkeys(merged_origins))


def is_local_runtime_mode():
    return env_bool('DJANGO_DEBUG', False) or env_str('DJANGO_ENV').lower() == 'development'


def local_private_network_hosts():
    hosts = []
    candidates = {'localhost', '127.0.0.1', socket.gethostname()}
    try:
        candidates.update(socket.gethostbyname_ex(socket.gethostname())[2])
    except socket.gaierror:
        pass
    try:
        for family, _, _, _, sockaddr in socket.getaddrinfo(socket.gethostname(), None):
            if family == socket.AF_INET and sockaddr:
                candidates.add(sockaddr[0])
    except socket.gaierror:
        pass

    for candidate in candidates:
        try:
            address = ipaddress.ip_address(candidate)
        except ValueError:
            hosts.append(candidate)
            continue
        if address.version == 4 and (address.is_private or address.is_loopback):
            hosts.append(candidate)

    return sorted(dict.fromkeys(hosts))


def build_database_config(default_sqlite_path):
    database_url = ''
    if ACTIVE_SETTINGS_MODULE.endswith('.test'):
        database_url = env_str('TEST_DATABASE_URL')
    database_url = database_url or env_str('DATABASE_URL') or env_str('OCTOBOX_DEFAULT_DATABASE_URL')

    if not database_url and env_bool('OCTOBOX_ALLOW_SQLITE_FALLBACK', False):
        return {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': default_sqlite_path,
        }

    parsed = dj_database_url.parse(
        database_url or LOCAL_POSTGRES_DATABASE_URL,
        conn_max_age=int(os.getenv('DB_CONN_MAX_AGE', '60')),
        ssl_require=env_bool('DB_SSL_REQUIRE', False),
    )

    if 'sqlite' in parsed.get('ENGINE', '') and not env_bool('OCTOBOX_ALLOW_SQLITE_FALLBACK', False):
        raise ImproperlyConfigured(
            'SQLite nao e mais fallback padrao do OctoBox. '
            'Configure DATABASE_URL/TEST_DATABASE_URL com PostgreSQL ou defina '
            'OCTOBOX_ALLOW_SQLITE_FALLBACK=1 apenas para diagnosticos legados.'
        )

    return parsed


def build_cache_config(*, key_prefix_override=None, key_function=None):
    """Monta a config de um alias de CACHES.

    key_prefix_override: quando passado, substitui o KEY_PREFIX calculado por
    build_box_cache_key_prefix(). Existe para os aliases 'sessions' e
    'platform' (ver Onda 4, docs/plans/ondas-correcao-tenancy-billing-
    2026-08-25.md) terem namespace PRÓPRIO e ESTÁVEL, deliberadamente
    diferente do 'default' — nunca devem colidir nem ganhar KEY_FUNCTION.

    key_function: callable (ou dotted path) passado como KEY_FUNCTION do
    alias. Só o 'default' recebe — particiona toda chave pelo schema ATIVO
    NO MOMENTO DA CHAMADA (diferente de KEY_PREFIX, congelado no boot).
    Ver shared_support.box_runtime.box_partitioned_key_function.
    """
    cache_url = env_str('REDIS_URL') or env_str('CACHE_URL')
    cache_key_prefix = key_prefix_override or build_box_cache_key_prefix(env_str('CACHE_KEY_PREFIX', 'octobox'))
    if cache_url:
        config = {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': cache_url,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'IGNORE_EXCEPTIONS': env_bool('CACHE_IGNORE_EXCEPTIONS', True),
                # 🚀 Segurança de Elite (Ghost Hardening): Insecure Deserialization
                # Usamos JSON em vez do padrão (Pickle) para evitar execução de código remoto
                # caso o servidor Redis venha a ser comprometido.
                'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
            },
            'KEY_PREFIX': cache_key_prefix,
        }
        if key_function is not None:
            config['KEY_FUNCTION'] = key_function
        return config

    # 🚀 Performance de Elite (Epic 8): Garante Redis em Produção
    if not is_local_runtime_mode():
         raise ImproperlyConfigured('REDIS_URL obrigatoria para Cache em Producao/Homologacao.')

    config = {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': key_prefix_override or build_box_cache_key_prefix('octobox-default'),
    }
    if key_function is not None:
        config['KEY_FUNCTION'] = key_function
    return config


LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'role-operations'
LOGOUT_REDIRECT_URL = 'login'
OPERATIONS_MANAGER_WORKSPACE_ENABLED = env_bool('OPERATIONS_MANAGER_WORKSPACE_ENABLED', False)

# Validade do link de recuperacao de senha da equipe (access/password_reset.py).
# O default do Django e 3 dias — folgado demais para conta de staff, que abre
# caixa, edita financeiro e mexe em cadastro de aluno. 30 minutos casa com o
# SESSION_COOKIE_AGE logo abaixo: mesma ordem de grandeza de confianca.
PASSWORD_RESET_TIMEOUT = env_int('PASSWORD_RESET_TIMEOUT', 1800)  # 30 minutos

# 🚀 Segurança de Elite (Fintech Hardening): Session Lifecycle
# Sessão expira em 30 minutos de inatividade para evitar sessões órfãs.
SESSION_COOKIE_AGE = 1800  # 30 minutos
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# 🚀 Performance AAA (Ghost Session): Sessões 100% na RAM em vez de disco/SQL
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
#
# ONDA 4, PASSO 0 (2026-08-26) — pré-requisito BLOQUEANTE antes de qualquer
# KEY_FUNCTION particionada por schema entrar no alias 'default'.
#
# Por que a sessão NÃO PODE dividir alias com um cache futuro particionado
# por tenant: a ordem dos middlewares faz SessionMiddleware ler a sessão
# ANTES do tenant existir (search_path ainda herdado da conexão anterior,
# CONN_MAX_AGE=60) e salvar DEPOIS que TenantBySessionMiddleware já setou o
# schema do box. Se o cache particionasse por schema, a leitura e a escrita
# da MESMA sessão cairiam em chaves DIFERENTES dentro do mesmo request —
# resultado determinístico: SessionStore.save() não acha a chave de
# origem, levanta UpdateError -> SessionInterrupted -> HTTP 400 no primeiro
# request autenticado. Em path público (sessão nunca resolve tenant), o
# efeito é logout silencioso: toda visita a '/', '/box/', '/aluno/' etc.
# é tratada como sessão nova.
#
# Este alias usa Redis/backend idêntico ao 'default', mas com KEY_PREFIX
# PRÓPRIO — nunca deve ganhar KEY_FUNCTION, mesmo que 'default' venha a
# ter uma no futuro. Trocar o prefixo aqui invalida sessões ativas no
# deploy (mesmo custo operacional que a KEY_FUNCTION completa: avisar
# relogin geral antes de subir, não é "ciclo frio").
SESSION_CACHE_ALIAS = 'sessions'

# Mandatory SECRET_KEY check (Epic 8 Security Hardening)
SECRET_KEY = env_str('DJANGO_SECRET_KEY') or env_str('SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured(
        'DJANGO_SECRET_KEY deve ser definida como variavel de ambiente ou no arquivo .env.'
    )

PHONE_BLIND_INDEX_KEY = env_str('PHONE_BLIND_INDEX_KEY', 'dev-default-blind-index-key')

# Stripe — credenciais e price IDs do programa Early Adopters.
# Os Price IDs sao criados no Stripe Dashboard (Catalog → Products) e copiados aqui via .env.
# Quando vazios, o checkout publico degrada para fluxo manual (Renan contata via WhatsApp).
STRIPE_SECRET_KEY = env_str('STRIPE_SECRET_KEY', '')
STRIPE_PUBLISHABLE_KEY = env_str('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_WEBHOOK_SECRET = env_str('STRIPE_WEBHOOK_SECRET', '')
STRIPE_PRICE_EARLY_MONTHLY = env_str('STRIPE_PRICE_EARLY_MONTHLY', '')
STRIPE_PRICE_EARLY_ANNUAL = env_str('STRIPE_PRICE_EARLY_ANNUAL', '')

# Superdev — conta unica de suporte anexada a TODO box provisionado.
# Vive em public (auth e SHARED_APP), entao um so usuario serve a todos os boxes.
# Anexado como Membership OWNER (is_primary_box=False) em control.services.provision_box.
# Crie/garanta a conta com: manage.py bootstrap_superdev
# SUPERDEV_AUTO_ATTACH=False e o kill-switch (desliga o anexo automatico).
SUPERDEV_USERNAME = env_str('SUPERDEV_USERNAME', 'superdev')
SUPERDEV_EMAIL = env_str('SUPERDEV_EMAIL', 'superdev@octoboxfit.com.br')
SUPERDEV_AUTO_ATTACH = env_bool('SUPERDEV_AUTO_ATTACH', True)

# 🚀 Segurança de Elite (Hardening): Chave de Blind Index
if not is_local_runtime_mode():
    if PHONE_BLIND_INDEX_KEY == 'dev-default-blind-index-key' or not PHONE_BLIND_INDEX_KEY:
        raise ImproperlyConfigured("PHONE_BLIND_INDEX_KEY não configurada ou usando valor padrão em Produção.")

ALLOWED_HOSTS = env_list_alias(('DJANGO_ALLOWED_HOSTS', 'ALLOWED_HOSTS'), 'localhost,127.0.0.1')
CSRF_TRUSTED_ORIGINS = env_list_alias(('DJANGO_CSRF_TRUSTED_ORIGINS', 'CSRF_TRUSTED_ORIGINS'))

if is_local_runtime_mode():
    local_hosts = local_private_network_hosts()
    ALLOWED_HOSTS = sorted(dict.fromkeys([*ALLOWED_HOSTS, *local_hosts]))
    local_trusted_origins = []
    for host in local_hosts:
        local_trusted_origins.append(f'http://{host}')
        local_trusted_origins.append(f'https://{host}')
    CSRF_TRUSTED_ORIGINS = sorted(dict.fromkeys([*CSRF_TRUSTED_ORIGINS, *local_trusted_origins]))

ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS = merge_public_host_contract(
    ALLOWED_HOSTS,
    CSRF_TRUSTED_ORIGINS,
    extra_hosts=[env_str('RENDER_EXTERNAL_HOSTNAME')],
)

# 🚀 Segurança de Elite (Ghost Hardening): CSRF Fail-Safe
if not is_local_runtime_mode() and not CSRF_TRUSTED_ORIGINS:
     # Em produção, a ausência de CSRF_TRUSTED_ORIGINS bloqueará todos os POSTs (403 Forbidden).
     # Isso é um erro comum de configuração que "quebra" o sistema no deploy.
     import logging
     logging.getLogger('django.security').warning("CSRF_TRUSTED_ORIGINS vazia em Produção. POSTs podem falhar.")

# ---------------------------------------------------------------------------
# django-tenants: SHARED_APPS + TENANT_APPS
#
# SHARED_APPS = apps que vivem em public schema (cross-tenant).
# TENANT_APPS = apps que vivem em box_xxx schemas (per-tenant).
#
# INSTALLED_APPS = SHARED_APPS + TENANT_APPS (django-tenants exige esta estrutura).
# django_tenants DEVE ser o primeiro em SHARED_APPS.
# ---------------------------------------------------------------------------

SHARED_APPS = [
    # django-tenants obrigatório primeiro
    'django_tenants',

    # Django core (cross-tenant)
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Control plane da plataforma (Box, Domain, Membership, BoxProvisioningEvent)
    'control.apps.ControlConfig',

    # Cross-tenant por design: existem ANTES de qualquer tenant
    'signup.apps.SignupConfig',
    'integrations.apps.IntegrationsConfig',

    # Identidade do aluno cross-box (migração Sprint 2)
    'student_identity.apps.StudentIdentityConfig',

    # Shared support (sem modelos de domínio)
    'shared_support.apps.SharedSupportConfig',

    # Hub de rede cross-tenant: agregados anonimos de canal por cohort de
    # box (Onda 8 do plano de ML de leads). So contagem, nunca dado
    # individual de aluno/lead.
    'intelligence_network.apps.IntelligenceNetworkConfig',

    # Índice de conhecimento do repositório (RAG interno). É conteúdo do REPO,
    # idêntico para todo box → vive no public, indexado UMA vez (não por tenant).
    # Antes era TENANT_APP: duplicava ~13k chunks por box e quebrava a CLI no public.
    'knowledge.apps.KnowledgeConfig',
]

TENANT_APPS = [
    # django.contrib.contenttypes duplicado em TENANT para FK per-tenant funcionar
    'django.contrib.contenttypes',

    # Âncora histórica de TODAS as migrations de domínio
    'boxcore.apps.BoxcoreConfig',

    # Facades de domínio (sem migrations próprias — dependem de boxcore)
    'students.apps.StudentsConfig',
    'finance.apps.FinanceConfig',
    'operations.apps.OperationsConfig',
    'auditing.apps.AuditingConfig',
    'communications.apps.CommunicationsConfig',

    # Features per-tenant
    'dashboard.apps.DashboardConfig',
    'access.apps.AccessConfig',
    'catalog.apps.CatalogConfig',
    'guide.apps.GuideConfig',
    'jobs.apps.JobsConfig',
    'quick_sales.apps.QuickSalesConfig',
    'api.apps.ApiConfig',

    # Camada de inteligencia operacional (feature layer, sem migrations
    # dependentes de boxcore — nasce com estado proprio, so fatos, nunca
    # verdade primaria). Ver docs/architecture/operational-intelligence-ml-layer.md.
    'intelligence.apps.IntelligenceConfig',

    # App do aluno (views + modelos per-tenant como Student, SessionWorkout)
    'student_app.apps.StudentAppConfig',
]

# django-tenants requer que INSTALLED_APPS = list(SHARED_APPS) + TENANT_APPS
# (sem duplicatas de SHARED_APPS em TENANT_APPS, exceto contenttypes)
INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

PROJECT_RAG_REMOTE_LLM_ENABLED = env_bool('PROJECT_RAG_REMOTE_LLM_ENABLED', False)
PROJECT_RAG_GENERATION_PROVIDER = env_str('PROJECT_RAG_GENERATION_PROVIDER', 'openai')   # 'openai' | 'anthropic' | 'extractive'
PROJECT_RAG_REMOTE_MODEL = env_str('PROJECT_RAG_REMOTE_MODEL', 'gpt-4o-mini')            # openai: gpt-4o-mini | anthropic: claude-haiku-4-5-20251001
PROJECT_RAG_REMOTE_MAX_TOKENS = env_int('PROJECT_RAG_REMOTE_MAX_TOKENS', 1024)
PROJECT_RAG_REMOTE_TIMEOUT_SECONDS = env_int('PROJECT_RAG_REMOTE_TIMEOUT_SECONDS', 30)
PROJECT_RAG_MAX_CONTEXT_CHARS = env_int('PROJECT_RAG_MAX_CONTEXT_CHARS', 12000)
PROJECT_RAG_EMBEDDINGS_ENABLED = env_bool('PROJECT_RAG_EMBEDDINGS_ENABLED', False)
PROJECT_RAG_EMBEDDING_PROVIDER = env_str('PROJECT_RAG_EMBEDDING_PROVIDER', 'openai')     # 'openai' | 'voyage' | 'disabled'
PROJECT_RAG_EMBEDDING_MODEL = env_str('PROJECT_RAG_EMBEDDING_MODEL', 'text-embedding-3-small')  # voyage: voyage-3-lite | voyage-code-3
PROJECT_RAG_EMBEDDING_DIMENSIONS = env_int('PROJECT_RAG_EMBEDDING_DIMENSIONS', 256)
PROJECT_RAG_EMBEDDING_TIMEOUT_SECONDS = env_int('PROJECT_RAG_EMBEDDING_TIMEOUT_SECONDS', 30)
PROJECT_RAG_EMBEDDING_BATCH_SIZE = env_int('PROJECT_RAG_EMBEDDING_BATCH_SIZE', 64)
PROJECT_RAG_EMBEDDING_MIN_SCORE = env_float('PROJECT_RAG_EMBEDDING_MIN_SCORE', 0.15)

MIDDLEWARE = [
    # C2 FIX: PrometheusBeforeMiddleware ANTES de qualquer middleware de app
    # (antes era WebhookIdempotencyMiddleware — que fazia DB query sem tenant)
    'monitoring.prometheus_middleware.PrometheusBeforeMiddleware',

    # Segurança de rede (não precisa de tenant)
    'django.middleware.security.SecurityMiddleware',
    # Nota: o middleware customizado e `shared_support.security.RequestSecurityMiddleware`
    # (carregado mais abaixo, depois do tenant). Referencia legada removida.
    'whitenoise.middleware.WhiteNoiseMiddleware',

    # Sessão ANTES do tenant (tenant depende de session['active_box_id'])
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',

    # Auth ANTES do tenant (TenantBySessionMiddleware precisa de request.user)
    'django.contrib.auth.middleware.AuthenticationMiddleware',

    # Tenant por sessão — seta connection.tenant para todos os requests autenticados
    # C1 FIX: sempre chama set_tenant() ou set_schema_to_public() — nunca herda search_path
    'control.middleware.TenantBySessionMiddleware',

    # C2 FIX: WebhookIdempotencyMiddleware DEPOIS do tenant (faz DB query)
    # Antes estava no topo — causava query sem search_path correto
    'integrations.middleware.WebhookIdempotencyMiddleware',

    # Outros middlewares de app (precisam de tenant já setado)
    'shared_support.request_timing_middleware.RequestTimingMiddleware',
    'shared_support.security.honeypot_middleware.HoneypotMiddleware',
    'shared_support.security.fingerprint_middleware.SessionFingerprintMiddleware',
    'shared_support.security.RequestSecurityMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    # Auth do aluno — resolve tenant DO ALUNO antes de qualquer query de domínio (Sprint 4)
    'student_app.middleware.student_auth.StudentAuthMiddleware',
]

STUDENT_LOGIN_URL = '/aluno/auth/login/'
STUDENT_APP_URL_PREFIX = '/aluno/'
STUDENT_AUDIT_ASYNC = False

# ---------------------------------------------------------------------------
# django-tenants configuration
# ---------------------------------------------------------------------------

# Modelo que representa o tenant (Box) — deve ser o primeiro INSTALLED_APP de SHARED_APPS
TENANT_MODEL = 'control.Box'

# Modelo que mapeia domínio → tenant (Fase 2: subdomain; Fase 1: session-based)
TENANT_DOMAIN_MODEL = 'control.Domain'

# URLs para o schema public (login, signup, admin de plataforma, webhook, healthcheck)
PUBLIC_SCHEMA_URLCONF = 'config.urls_public'

# Schema name do public (padrão django-tenants)
PUBLIC_SCHEMA_NAME = 'public'

# Roteador de banco obrigatório pelo django-tenants
DATABASE_ROUTERS = ['django_tenants.routers.TenantSyncRouter']

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'access.context_processors.role_navigation',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

DATABASES = {
    'default': build_database_config(BASE_DIR / 'db.sqlite3')
}

# django-tenants exige backend customizado que adiciona schema_name à conexão.
# Substituir o ENGINE padrão pelo backend do django-tenants quando PostgreSQL for usado.
_default_db = DATABASES['default']
if _default_db.get('ENGINE') in (
    'django.db.backends.postgresql',
    'django.db.backends.postgresql_psycopg2',
    'django.db.backends.dummy',
) or _default_db.get('ENGINE', '').endswith('psycopg'):
    _default_db['ENGINE'] = 'django_tenants.postgresql_backend'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [path for path in [BASE_DIR / 'static'] if path.exists()]
# 🚀 Cache Estratégico (Epic 8 Performance)
# Aumentamos o TTL para 5 minutos (300s) para evitar recomputações frequentes de contagens pesadas no shell.
SHELL_COUNTS_CACHE_TTL_SECONDS = env_int('SHELL_COUNTS_CACHE_TTL_SECONDS', 300)
STUDENT_AGENDA_CACHE_TTL_SECONDS = env_int('STUDENT_AGENDA_CACHE_TTL_SECONDS', 120)
STUDENT_HOME_CACHE_TTL_SECONDS = env_int('STUDENT_HOME_CACHE_TTL_SECONDS', 30)
STUDENT_RM_CACHE_TTL_SECONDS = env_int('STUDENT_RM_CACHE_TTL_SECONDS', 300)
STUDENT_WOD_CACHE_TTL_SECONDS = env_int('STUDENT_WOD_CACHE_TTL_SECONDS', 21600)
STATIC_ASSET_SCAN_TTL_SECONDS = env_int('STATIC_ASSET_SCAN_TTL_SECONDS', 300)
STATIC_ASSET_VERSION = env_str('STATIC_ASSET_VERSION', env_str('RENDER_GIT_COMMIT', '1'))
# URL publica do GPT customizado SmartPlan (configurar apos publicar no chat.openai.com).
# Enquanto vazio, o card SmartPlan no editor mostra estado "em configuracao".
SMARTPLAN_GPT_URL = env_str('SMARTPLAN_GPT_URL', '')
STUDENT_APP_SESSION_COOKIE_NAME = env_str('STUDENT_APP_SESSION_COOKIE_NAME', 'octobox_student_session')
STUDENT_APP_SESSION_COOKIE_AGE = env_int('STUDENT_APP_SESSION_COOKIE_AGE', 604800)
STUDENT_GOOGLE_OAUTH_CLIENT_ID = env_str('STUDENT_GOOGLE_OAUTH_CLIENT_ID')
STUDENT_GOOGLE_OAUTH_CLIENT_SECRET = env_str('STUDENT_GOOGLE_OAUTH_CLIENT_SECRET')
STUDENT_APPLE_OAUTH_CLIENT_ID = env_str('STUDENT_APPLE_OAUTH_CLIENT_ID')
STUDENT_APPLE_OAUTH_TEAM_ID = env_str('STUDENT_APPLE_OAUTH_TEAM_ID')
STUDENT_APPLE_OAUTH_KEY_ID = env_str('STUDENT_APPLE_OAUTH_KEY_ID')
STUDENT_APPLE_OAUTH_PRIVATE_KEY = env_str('STUDENT_APPLE_OAUTH_PRIVATE_KEY')
ADMIN_URL_PATH = f"{env_str('DJANGO_ADMIN_URL_PATH', 'painel-interno').strip('/')}/"
LOGIN_RATE_LIMIT_WINDOW_SECONDS = env_int('LOGIN_RATE_LIMIT_WINDOW_SECONDS', 300)
LOGIN_RATE_LIMIT_MAX_REQUESTS = env_int('LOGIN_RATE_LIMIT_MAX_REQUESTS', 8)
ADMIN_RATE_LIMIT_WINDOW_SECONDS = env_int('ADMIN_RATE_LIMIT_WINDOW_SECONDS', 300)
ADMIN_RATE_LIMIT_MAX_REQUESTS = env_int('ADMIN_RATE_LIMIT_MAX_REQUESTS', 12)
WRITE_RATE_LIMIT_WINDOW_SECONDS = env_int('WRITE_RATE_LIMIT_WINDOW_SECONDS', 60)
WRITE_RATE_LIMIT_MAX_REQUESTS = env_int('WRITE_RATE_LIMIT_MAX_REQUESTS', 30)
EXPORT_RATE_LIMIT_WINDOW_SECONDS = env_int('EXPORT_RATE_LIMIT_WINDOW_SECONDS', 3600)  # 1 hora
EXPORT_RATE_LIMIT_MAX_REQUESTS = env_int('EXPORT_RATE_LIMIT_MAX_REQUESTS', 2)
ANTI_EXFILTRATION_WINDOW_SECONDS = env_int('ANTI_EXFILTRATION_WINDOW_SECONDS', 300)
ANTI_EXFILTRATION_MAX_REQUESTS = env_int('ANTI_EXFILTRATION_MAX_REQUESTS', 60)
DASHBOARD_RATE_LIMIT_WINDOW_SECONDS = env_int('DASHBOARD_RATE_LIMIT_WINDOW_SECONDS', 60)
DASHBOARD_RATE_LIMIT_MAX_REQUESTS = env_int('DASHBOARD_RATE_LIMIT_MAX_REQUESTS', 45)
OPERATIONAL_WHATSAPP_REPEAT_BLOCK_HOURS = env_int('OPERATIONAL_WHATSAPP_REPEAT_BLOCK_HOURS', 24)
HEAVY_READ_RATE_LIMIT_WINDOW_SECONDS = env_int('HEAVY_READ_RATE_LIMIT_WINDOW_SECONDS', 60)
HEAVY_READ_RATE_LIMIT_MAX_REQUESTS = env_int('HEAVY_READ_RATE_LIMIT_MAX_REQUESTS', 40)
AUTOCOMPLETE_RATE_LIMIT_WINDOW_SECONDS = env_int('AUTOCOMPLETE_RATE_LIMIT_WINDOW_SECONDS', 60)
AUTOCOMPLETE_RATE_LIMIT_MAX_REQUESTS = env_int('AUTOCOMPLETE_RATE_LIMIT_MAX_REQUESTS', 90)
SECURITY_TRUSTED_PROXY_IPS = env_list('SECURITY_TRUSTED_PROXY_IPS')
SECURITY_BLOCKED_IPS = env_list('SECURITY_BLOCKED_IPS')
SECURITY_BLOCKED_IP_RANGES = env_list('SECURITY_BLOCKED_IP_RANGES')
SECURITY_LOG_LEVEL = env_str('SECURITY_LOG_LEVEL', 'WARNING')
STUDENT_APP_SESSION_COOKIE_NAME = env_str('STUDENT_APP_SESSION_COOKIE_NAME', 'octobox_student_session')
STUDENT_APP_SESSION_COOKIE_AGE = env_int('STUDENT_APP_SESSION_COOKIE_AGE', 604800)
STUDENT_OAUTH_PUBLIC_BASE_URL = env_str('STUDENT_OAUTH_PUBLIC_BASE_URL')
STUDENT_WEB_PUSH_VAPID_PUBLIC_KEY = env_str('STUDENT_WEB_PUSH_VAPID_PUBLIC_KEY')
STUDENT_WEB_PUSH_VAPID_PRIVATE_KEY = env_str('STUDENT_WEB_PUSH_VAPID_PRIVATE_KEY')
STUDENT_WEB_PUSH_VAPID_CLAIMS_SUBJECT = env_str('STUDENT_WEB_PUSH_VAPID_CLAIMS_SUBJECT')
STUDENT_GOOGLE_OAUTH_CLIENT_ID = env_str('STUDENT_GOOGLE_OAUTH_CLIENT_ID')
STUDENT_GOOGLE_OAUTH_CLIENT_SECRET = env_str('STUDENT_GOOGLE_OAUTH_CLIENT_SECRET')
STUDENT_APPLE_OAUTH_CLIENT_ID = env_str('STUDENT_APPLE_OAUTH_CLIENT_ID')
STUDENT_APPLE_OAUTH_TEAM_ID = env_str('STUDENT_APPLE_OAUTH_TEAM_ID')
STUDENT_APPLE_OAUTH_KEY_ID = env_str('STUDENT_APPLE_OAUTH_KEY_ID')
STUDENT_APPLE_OAUTH_PRIVATE_KEY = env_str('STUDENT_APPLE_OAUTH_PRIVATE_KEY')
STUDENT_EMAIL_PROVIDER = env_str('STUDENT_EMAIL_PROVIDER', 'smtp')
STUDENT_EMAIL_FROM = env_str('STUDENT_EMAIL_FROM')
STUDENT_RESEND_API_KEY = env_str('STUDENT_RESEND_API_KEY')
STUDENT_RESEND_WEBHOOK_SECRET = env_str('STUDENT_RESEND_WEBHOOK_SECRET')
# Sem isto, o backend SMTP do Django nao aplica timeout nenhum ao socket —
# um provedor de email travado prenderia a thread de envio (background ou
# nao) para sempre. A confirmacao de pagamento e o onboarding do Early
# Adopter passam por aqui (finance/payment_notifications.py, signup/services.py).
EMAIL_TIMEOUT = env_int('EMAIL_TIMEOUT', 10)
STUDENT_INVITE_LANDING_RATE_LIMIT_WINDOW_SECONDS = env_int('STUDENT_INVITE_LANDING_RATE_LIMIT_WINDOW_SECONDS', 300)
STUDENT_INVITE_LANDING_RATE_LIMIT_MAX_REQUESTS = env_int('STUDENT_INVITE_LANDING_RATE_LIMIT_MAX_REQUESTS', 20)
STUDENT_OAUTH_CALLBACK_RATE_LIMIT_WINDOW_SECONDS = env_int('STUDENT_OAUTH_CALLBACK_RATE_LIMIT_WINDOW_SECONDS', 300)
STUDENT_OAUTH_CALLBACK_RATE_LIMIT_MAX_REQUESTS = env_int('STUDENT_OAUTH_CALLBACK_RATE_LIMIT_MAX_REQUESTS', 12)
STUDENT_OPEN_BOX_INVITE_WINDOW_HOURS = env_int('STUDENT_OPEN_BOX_INVITE_WINDOW_HOURS', 24)
STUDENT_OPEN_BOX_INVITE_LIMIT_PER_WINDOW = env_int('STUDENT_OPEN_BOX_INVITE_LIMIT_PER_WINDOW', 25)
STUDENT_INVITE_CREATION_ACTOR_ALERT_WINDOW_SECONDS = env_int('STUDENT_INVITE_CREATION_ACTOR_ALERT_WINDOW_SECONDS', 900)
STUDENT_INVITE_CREATION_ACTOR_ALERT_THRESHOLD = env_int('STUDENT_INVITE_CREATION_ACTOR_ALERT_THRESHOLD', 12)
STUDENT_INVITE_CREATION_BOX_ALERT_WINDOW_SECONDS = env_int('STUDENT_INVITE_CREATION_BOX_ALERT_WINDOW_SECONDS', 900)
STUDENT_INVITE_CREATION_BOX_ALERT_THRESHOLD = env_int('STUDENT_INVITE_CREATION_BOX_ALERT_THRESHOLD', 20)
STUDENT_INVITE_ACCEPT_IP_ALERT_WINDOW_SECONDS = env_int('STUDENT_INVITE_ACCEPT_IP_ALERT_WINDOW_SECONDS', 600)
STUDENT_INVITE_ACCEPT_IP_ALERT_THRESHOLD = env_int('STUDENT_INVITE_ACCEPT_IP_ALERT_THRESHOLD', 8)
STUDENT_INVITE_ACCEPT_BOX_ALERT_WINDOW_SECONDS = env_int('STUDENT_INVITE_ACCEPT_BOX_ALERT_WINDOW_SECONDS', 600)
STUDENT_INVITE_ACCEPT_BOX_ALERT_THRESHOLD = env_int('STUDENT_INVITE_ACCEPT_BOX_ALERT_THRESHOLD', 12)

# Gate de entrada com PAR-Q + termo (Onda A). Default OFF: o gate so liga em staging
# apos validacao. Envolve os redirects de consentimento e de clearance no dispatch.
STUDENT_CONSENT_GATE_ENABLED = env_bool('STUDENT_CONSENT_GATE_ENABLED', False)

# Forçar DEBUG para loggers de segurança (modo depuração solicitado).
EFFECTIVE_SECURITY_LOG_LEVEL = 'DEBUG' if is_local_runtime_mode() else SECURITY_LOG_LEVEL
DATA_UPLOAD_MAX_MEMORY_SIZE = env_int('DATA_UPLOAD_MAX_MEMORY_SIZE', 15728640)
FILE_UPLOAD_MAX_MEMORY_SIZE = env_int('FILE_UPLOAD_MAX_MEMORY_SIZE', 15728640)
DATA_UPLOAD_MAX_NUMBER_FIELDS = env_int('DATA_UPLOAD_MAX_NUMBER_FIELDS', 200)
JOB_RETRY_SWEEP_LIMIT = env_int('JOB_RETRY_SWEEP_LIMIT', 25)
WEBHOOK_RETRY_SWEEP_LIMIT = env_int('WEBHOOK_RETRY_SWEEP_LIMIT', 25)
STRIPE_RETRY_SWEEP_LIMIT = env_int('STRIPE_RETRY_SWEEP_LIMIT', 25)
STRIPE_RECONCILE_WINDOW_DAYS = env_int('STRIPE_RECONCILE_WINDOW_DAYS', 7)
STRIPE_RECONCILE_LIMIT = env_int('STRIPE_RECONCILE_LIMIT', 100)
LEAD_IMPORT_NIGHT_WINDOW_START_HOUR = env_int('LEAD_IMPORT_NIGHT_WINDOW_START_HOUR', 0)
LEAD_IMPORT_NIGHT_WINDOW_END_HOUR = env_int('LEAD_IMPORT_NIGHT_WINDOW_END_HOUR', 4)
LEAD_IMPORT_NIGHT_SWEEP_LIMIT = env_int('LEAD_IMPORT_NIGHT_SWEEP_LIMIT', 25)
ALERT_SIREN_LOW_BACKLOG_THRESHOLD = env_int('ALERT_SIREN_LOW_BACKLOG_THRESHOLD', 1)
ALERT_SIREN_MEDIUM_BACKLOG_THRESHOLD = env_int('ALERT_SIREN_MEDIUM_BACKLOG_THRESHOLD', 5)
ALERT_SIREN_HIGH_BACKLOG_THRESHOLD = env_int('ALERT_SIREN_HIGH_BACKLOG_THRESHOLD', 12)
ALERT_SIREN_HIGH_SKIP_THRESHOLD = env_int('ALERT_SIREN_HIGH_SKIP_THRESHOLD', 5)
ALERT_SIREN_MEDIUM_JOB_LIMIT_CAP = env_int('ALERT_SIREN_MEDIUM_JOB_LIMIT_CAP', 10)
ALERT_SIREN_MEDIUM_WEBHOOK_LIMIT_CAP = env_int('ALERT_SIREN_MEDIUM_WEBHOOK_LIMIT_CAP', 10)
ALERT_SIREN_HIGH_JOB_LIMIT_CAP = env_int('ALERT_SIREN_HIGH_JOB_LIMIT_CAP', 5)
ALERT_SIREN_HIGH_WEBHOOK_LIMIT_CAP = env_int('ALERT_SIREN_HIGH_WEBHOOK_LIMIT_CAP', 0)
WOD_ACTION_TELEMETRY_ENABLED = env_bool('WOD_ACTION_TELEMETRY_ENABLED', True)
WOD_ACTION_TELEMETRY_SAMPLE_RATE = env_float('WOD_ACTION_TELEMETRY_SAMPLE_RATE', 1.0)
WOD_APPROVAL_POLICY = env_str('WOD_APPROVAL_POLICY', 'strict')

# 🔒 Segurança Institucional White Hat (Bug Bounty Fixes)
# Força o browser do cliente a nunca se conectar com HTTP por 1 ano (prevenindo mitm_downgrade)
SECURE_HSTS_SECONDS = 31536000 
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
# Ocultar o Header Type (previne que atacantes explorem sniff de arquivos para XSS)
SECURE_CONTENT_TYPE_NOSNIFF = True
# Em ambiente de produção/homologação, o redirect HTTPS deve ser controlado por env.
SECURE_SSL_REDIRECT = env_bool('ENFORCE_SSL', False)

CACHES = {
    # Onda 4 (2026-08-26): KEY_FUNCTION particiona toda chave pelo schema
    # ATIVO NO MOMENTO DA CHAMADA — corrige o vazamento que o KEY_PREFIX
    # sozinho não fechava (congelado no boot, antes de qualquer tenant
    # existir — ver docstring de build_cache_config). Pré-requisitos que
    # tornam isto seguro (Onda 4, Passo 0 e Passo 2) já estavam prontos:
    # sessão vive em alias próprio sem KEY_FUNCTION (abaixo) e a thread de
    # job em background herda o schema certo antes de gravar/ler.
    'default': build_cache_config(key_function=box_partitioned_key_function),
    # Onda 4, Passo 0 — ver comentário longo em SESSION_CACHE_ALIAS acima.
    # Prefixo próprio e estável: NUNCA deve receber KEY_FUNCTION.
    'sessions': build_cache_config(key_prefix_override='octobox-sessions'),
    # Onda 4, Passo 3 — chaves GLOBAIS por natureza (papel/honeypot indexado
    # por user_id — auth_user só existe em public; anti-card-testing, que
    # protege uma única conta Stripe compartilhada por todos os boxes).
    # Nunca deve receber KEY_FUNCTION — ver shared_support/platform_cache.py
    # para o motivo completo e a lista de consumidores.
    'platform': build_cache_config(key_prefix_override='octobox-platform'),
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        # Carimba cada registro com o box ativo (isolamento forense da Fase 1).
        # Concern transversal -> um unico processador (filosofia Signal Mesh).
        'box_runtime': {
            '()': 'shared_support.box_log_filter.BoxRuntimeLogFilter',
        },
    },
    'formatters': {
        'box_aware': {
            'format': '[%(asctime)s] %(levelname)s [box=%(runtime_slug)s] %(name)s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'filters': ['box_runtime'],
            'formatter': 'box_aware',
        },
    },
    'loggers': {
        'octobox.security': {
            'handlers': ['console'],
            'level': EFFECTIVE_SECURITY_LOG_LEVEL,
            'propagate': False,
        },
        'octobox.access': {
            'handlers': ['console'],
            'level': EFFECTIVE_SECURITY_LOG_LEVEL,
            'propagate': False,
        },
        'octobox.operations.wod': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'octobox.security.honeypot': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
