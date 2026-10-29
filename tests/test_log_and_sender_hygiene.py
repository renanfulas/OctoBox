"""Nada de token em log de acesso nem remetente @localhost."""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _gunicorn_config():
    spec = importlib.util.spec_from_file_location('gunicorn_conf', ROOT / 'gunicorn.conf.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gunicorn_access_log_drops_query_string_and_referer():
    log_format = _gunicorn_config().access_log_format

    assert '%(U)s' in log_format
    assert '%(r)s' not in log_format  # linha da requisicao com ?token=
    assert '%(q)s' not in log_format
    assert '%(f)s' not in log_format  # referer tambem carrega o link magico


def test_nginx_site_logs_with_the_format_without_query_string():
    conf = (ROOT / 'infra/hostgator-vps/nginx/app.octoboxfit.com.br.conf').read_text(encoding='utf-8')
    log_format = next(line for line in conf.splitlines() if line.startswith('log_format octobox_sem_query'))

    assert '$uri' in log_format
    assert '$request ' not in log_format and '$request_uri' not in log_format and '$args' not in log_format
    assert '$http_referer' not in log_format
    assert conf.count('access_log /var/log/nginx/access.log octobox_sem_query;') == conf.count('server {')


def _production_setting(name: str, **env) -> str:
    # Producao exige segredo/banco/cache reais so para importar; nada conecta aqui.
    process_env = {
        **os.environ, 'DJANGO_SETTINGS_MODULE': 'config.settings.production',
        'DJANGO_SECRET_KEY': 'x' * 64, 'DATABASE_URL': 'postgresql://u:p@127.0.0.1:1/x',
        'REDIS_URL': 'redis://127.0.0.1:1/0', 'STUDENT_EMAIL_FROM': '', 'DEFAULT_FROM_EMAIL': '',
        'SERVER_EMAIL': '', 'SENTRY_DSN': '', **env,
    }
    result = subprocess.run(
        [sys.executable, '-c', f'from django.conf import settings; print(settings.{name})'],
        cwd=ROOT, env=process_env, capture_output=True, text=True, timeout=60, check=True,
    )
    return result.stdout.strip().splitlines()[-1]


def test_production_senders_never_use_localhost():
    assert _production_setting('DEFAULT_FROM_EMAIL') == 'OctoBox <nao-responda@octoboxfit.com.br>'
    assert _production_setting('SERVER_EMAIL') == 'OctoBox <nao-responda@octoboxfit.com.br>'
    curva = 'Curva <ola@octoboxfit.com.br>'
    assert _production_setting('DEFAULT_FROM_EMAIL', STUDENT_EMAIL_FROM=curva) == curva
