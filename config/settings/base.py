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
from config.env_loader import load_project_env
from shared_support.box_runtime import build_box_cache_key_prefix

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ACTIVE_SETTINGS_MODULE = os.getenv('DJANGO_SETTINGS_MODULE', '').strip().lower()

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
    database_url = env_str('DATABASE_URL')
    if database_url:
        return dj_database_url.parse(database_url, conn_max_age=int(os.getenv('DB_CONN_MAX_AGE', '60')), ssl_require=env_bool('DB_SSL_REQUIRE', False))

    return {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': default_sqlite_path,
    }


from django.core.exceptions import ImproperlyConfigured

def build_cache_config():
    cache_url = env_str('REDIS_URL') or env_str('CACHE_URL')
    cache_key_prefix = build_box_cache_key_prefix(env_str('CACHE_KEY_PREFIX', 'octobox'))
    if cache_url:
        return {
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

    # 🚀 Performance de Elite (Epic 8): Garante Redis em Produção
    if not is_local_runtime_mode():
         raise ImproperlyConfigured('REDIS_URL obrigatoria para Cache em Producao/Homologacao.')

    return {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': build_box_cache_key_prefix('octobox-default'),
    }


LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'role-operations'
LOGOUT_REDIRECT_URL = 'login'
OPERATIONS_MANAGER_WORKSPACE_ENABLED = env_bool('OPERATIONS_MANAGER_WORKSPACE_ENABLED', False)

# 🚀 Segurança de Elite (Fintech Hardening): Session Lifecycle
# Sessão expira em 30 minutos de inatividade para evitar sessões órfãs.
SESSION_COOKIE_AGE = 1800  # 30 minutos
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# 🚀 Performance AAA (Ghost Session): Sessões 100% na RAM em vez de disco/SQL
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Mandatory SECRET_KEY check (Epic 8 Security Hardening)
SECRET_KEY = env_str('DJANGO_SECRET_KEY') or env_str('SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured(
        'DJANGO_SECRET_KEY deve ser definida como variavel de ambiente ou no arquivo .env.'
    )

PHONE_BLIND_INDEX_KEY = env_str('PHONE_BLIND_INDEX_KEY', 'dev-default-blind-index-key')

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

# 🚀 Segurança de Elite (Ghost Hardening): CSRF Fail-Safe
if not is_local_runtime_mode() and not CSRF_TRUSTED_ORIGINS:
     # Em produção, a ausência de CSRF_TRUSTED_ORIGINS bloqueará todos os POSTs (403 Forbidden).
     # Isso é um erro comum de configuração que "quebra" o sistema no deploy.
     import logging
     logging.getLogger('django.security').warning("CSRF_TRUSTED_ORIGINS vazia em Produção. POSTs podem falhar.")

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

LOCAL_APPS = [
    'access.apps.AccessConfig',
    'api.apps.ApiConfig',
    'auditing.apps.AuditingConfig',
    'catalog.apps.CatalogConfig',
    'communications.apps.CommunicationsConfig',
    'dashboard.apps.DashboardConfig',
    'finance.apps.FinanceConfig',
    'guide.apps.GuideConfig',
    'jobs.apps.JobsConfig',
    'integrations.apps.IntegrationsConfig',
    'operations.apps.OperationsConfig',
    'students.apps.StudentsConfig',
    'boxcore.apps.BoxcoreConfig',
    'shared_support.apps.SharedSupportConfig',
]

INSTALLED_APPS = [*DJANGO_APPS, *LOCAL_APPS]

MIDDLEWARE = [
    'integrations.middleware.WebhookIdempotencyMiddleware',
    'monitoring.prometheus_middleware.PrometheusBeforeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'shared_support.security.honeypot_middleware.HoneypotMiddleware',
    'shared_support.security.fingerprint_middleware.SessionFingerprintMiddleware',
    'shared_support.security.RequestSecurityMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

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
STATIC_ASSET_SCAN_TTL_SECONDS = env_int('STATIC_ASSET_SCAN_TTL_SECONDS', 300)
STATIC_ASSET_VERSION = env_str('STATIC_ASSET_VERSION', env_str('RENDER_GIT_COMMIT', '1'))
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

# Forçar DEBUG para loggers de segurança (modo depuração solicitado).
EFFECTIVE_SECURITY_LOG_LEVEL = 'DEBUG' if is_local_runtime_mode() else SECURITY_LOG_LEVEL
DATA_UPLOAD_MAX_MEMORY_SIZE = env_int('DATA_UPLOAD_MAX_MEMORY_SIZE', 15728640)
FILE_UPLOAD_MAX_MEMORY_SIZE = env_int('FILE_UPLOAD_MAX_MEMORY_SIZE', 15728640)
DATA_UPLOAD_MAX_NUMBER_FIELDS = env_int('DATA_UPLOAD_MAX_NUMBER_FIELDS', 200)

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
    'default': build_cache_config()
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
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
        'octobox.security.honeypot': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
