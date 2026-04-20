"""
ARQUIVO: smoke HTTP base para homologacao e producao.

POR QUE ELE EXISTE:
- valida se o runtime publicado responde nas rotas basicas e, quando houver credenciais, testa login e rotas autenticadas.
- nao substitui a regressao explicita dos corredores do onboarding do aluno.
"""

from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar


def build_opener() -> urllib.request.OpenerDirector:
    cookie_jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    opener.cookie_jar = cookie_jar
    return opener


def request(opener, url, *, method="GET", data=None, headers=None):
    encoded_data = None
    if data is not None:
        encoded_data = urllib.parse.urlencode(data).encode("utf-8")

    req = urllib.request.Request(url, data=encoded_data, method=method)
    for header_name, header_value in (headers or {}).items():
        req.add_header(header_name, header_value)

    try:
        response = opener.open(req, timeout=30)
        body = response.read().decode("utf-8", errors="ignore")
        return response.getcode(), body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        return exc.code, body


def assert_status(url, status, expected_statuses):
    if status not in expected_statuses:
        raise RuntimeError(f"Smoke falhou em {url}: status {status}, esperado {sorted(expected_statuses)}.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Executa smoke test HTTP do OctoBox.")
    parser.add_argument("--base-url", required=True, help="Base URL do ambiente, ex: https://app.example.com")
    parser.add_argument("--username", default="", help="Usuario de login para smoke autenticado.")
    parser.add_argument("--password", default="", help="Senha de login para smoke autenticado.")
    parser.add_argument(
        "--public-path",
        action="append",
        default=[],
        help="Path publico para validar. Pode ser usado varias vezes.",
    )
    parser.add_argument(
        "--private-path",
        action="append",
        default=[],
        help="Path autenticado para validar apos login. Pode ser usado varias vezes.",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    opener = build_opener()

    public_paths = args.public_path or ["/api/v1/health/", "/login/"]
    private_paths = args.private_path or ["/dashboard/"]

    for path in public_paths:
        url = f"{base_url}{path}"
        status, _ = request(opener, url)
        assert_status(url, status, {200, 301, 302})
        print(f"[public-ok] {url} -> {status}")

    if not (args.username and args.password):
        print("[skip-auth] Credenciais ausentes; smoke autenticado nao executado.")
        return 0

    login_page_url = f"{base_url}/login/"
    status, _ = request(opener, login_page_url)
    assert_status(login_page_url, status, {200})

    csrf_token = None
    cookie_jar = getattr(opener, "cookie_jar", None)
    if cookie_jar is None:
        raise RuntimeError("Smoke falhou: cookie jar do cliente HTTP nao foi inicializado.")
    for cookie in cookie_jar:
        if cookie.name == "csrftoken":
            csrf_token = cookie.value
            break

    if not csrf_token:
        raise RuntimeError("Smoke falhou: cookie csrftoken nao foi emitido pelo login.")

    login_url = f"{base_url}/login/?next=/dashboard/"
    status, _ = request(
        opener,
        login_url,
        method="POST",
        data={
            "username": args.username,
            "password": args.password,
            "csrfmiddlewaretoken": csrf_token,
        },
        headers={
            "Referer": login_page_url,
        },
    )
    assert_status(login_url, status, {200, 301, 302})
    print(f"[login-ok] {login_url} -> {status}")

    for path in private_paths:
        url = f"{base_url}{path}"
        status, _ = request(opener, url)
        assert_status(url, status, {200, 301, 302})
        print(f"[private-ok] {url} -> {status}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - CLI guard
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
