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

import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def env_bool(name, default=False):
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {'1', 'true', 'yes', 'on'}


def env_list(name, default=''):
    raw_value = os.getenv(name, default)
    return [item.strip() for item in raw_value.split(',') if item.strip()]


def env_str(name, default=''):
    return os.getenv(name, default).strip()


def build_database_config(default_sqlite_path):
    database_url = env_str('DATABASE_URL')
    if database_url:
        return dj_database_url.parse(database_url, conn_max_age=int(os.getenv('DB_CONN_MAX_AGE', '60')), ssl_require=env_bool('DB_SSL_REQUIRE', False))
    return {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': default_sqlite_path,
    }


LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'role-operations'
LOGOUT_REDIRECT_URL = 'login'

SECRET_KEY = env_str('DJANGO_SECRET_KEY', 'dev-only-secret-key-change-me')

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS')

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
    'finance.apps.FinanceConfig',
    'jobs.apps.JobsConfig',
    'integrations.apps.IntegrationsConfig',
    'operations.apps.OperationsConfig',
    'students.apps.StudentsConfig',
    'boxcore.apps.BoxcoreConfig',
]

INSTALLED_APPS = [*DJANGO_APPS, *LOCAL_APPS]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
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

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')