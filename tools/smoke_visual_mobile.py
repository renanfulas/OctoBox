"""
ARQUIVO: smoke visual mobile (Playwright) do OctoBox.

POR QUE ELE EXISTE:
- Permite rodar um smoke visual repetível em mobile, gerando screenshots e um relatório com achados.
- Ajuda a capturar regressões de responsividade (overflow horizontal, layout quebrado, CTAs esmagados).

O QUE ESTE ARQUIVO FAZ:
1. Gera (ou reutiliza) uma sessão Django autenticada para o usuário `autotest`.
2. Navega uma lista de rotas HTML (com foco em telas, não endpoints de ação).
3. Captura screenshots em breakpoints mobile/tablet/desktop e registra sinais de erro.

COMO USAR:
  .\\.venv\\Scripts\\python.exe tools\\smoke_visual_mobile.py --base http://127.0.0.1:8005

OBSERVAÇÃO:
- Este script é "smoke": ele não tenta cobrir cenários com dados complexos ou rotas parametrizadas.
- Quando uma rota exigir parâmetros, o script pode tentar placeholders, mas pode marcar como NA.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as _dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "page"


def _fill_route_params(route: str) -> str:
    route = re.sub(r"<int:[^>]+>", "1", route)
    route = re.sub(r"<str:[^>]+>", "demo", route)
    route = re.sub(r"<slug:[^>]+>", "demo", route)
    route = re.sub(r"<path:[^>]+>", "demo", route)
    return route


def _looks_like_visual_html_path(path: str) -> bool:
    excluded = (
        "/api/",
        "/metrics/",
        "/painel-interno/",
        "/events/",
        "/stream/",
        "/acao/",
        "/lote/",
        "/drawer/",
        "/fragmentos/",
        "/fragments/",
        "/exportar/",
        "/webhook/",
        "/heartbeat/",
        "/lock/",
        "/progresso/",
        "/snapshot/",
        "/telemetry/",
    )
    return not any(part in path for part in excluded)


@dataclasses.dataclass(frozen=True)
class Breakpoint:
    label: str
    width: int
    height: int
    is_mobile: bool = True
    device_scale_factor: int = 2


def _iter_named_routes() -> Iterable[tuple[str, str | None]]:
    from django.urls import get_resolver
    from django.urls.resolvers import URLPattern, URLResolver

    def walk(prefix: str, resolver: URLResolver) -> Iterable[tuple[str, str | None]]:
        for entry in resolver.url_patterns:
            if isinstance(entry, URLPattern):
                route = prefix + str(entry.pattern)
                yield route, entry.name
            elif isinstance(entry, URLResolver):
                yield from walk(prefix + str(entry.pattern), entry)

    yield from walk("", get_resolver())


def _build_target_paths(base_paths: list[str]) -> list[str]:
    targets: list[str] = []
    seen: set[str] = set()

    allow_prefixes = (
        "/",
        "/login/",
        "/acessos/",
        "/dashboard/",
        "/entradas/",
        "/alunos/",
        "/financeiro/",
        "/grade-aulas/",
        "/mapa-sistema/",
        "/configuracoes-operacionais/",
        "/operacao/",
        "/aluno/",
        "/renan/",
    )

    for p in base_paths:
        if not p.startswith("/"):
            p = "/" + p
        p = _fill_route_params(p)
        if p != "/" and not p.endswith("/"):
            # Many HTML routes are canonical with trailing slash.
            # Don't force it for files like sw.js or manifest.webmanifest.
            if not any(p.endswith(suf) for suf in (".js", ".webmanifest")):
                p = p + "/"
        if p not in seen:
            seen.add(p)
            targets.append(p)

    # Add discoverable routes from URLConf (best-effort).
    for route, _name in _iter_named_routes():
        if not route:
            route = "/"
        if not route.startswith("/"):
            route = "/" + route
        route = _fill_route_params(route)
        if "<" in route or ">" in route:
            continue
        if not route.startswith(allow_prefixes):
            continue
        if not _looks_like_visual_html_path(route):
            continue
        if route != "/" and not route.endswith("/"):
            if not any(route.endswith(suf) for suf in (".js", ".webmanifest")):
                route = route + "/"
        if route not in seen:
            seen.add(route)
            targets.append(route)

    return targets


def _ensure_autotest_user(password: str) -> None:
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user, created = User.objects.get_or_create(
        username="autotest",
        defaults={"email": "autotest@example.com"},
    )
    if created:
        user.set_password(password)
    user.is_staff = True
    user.is_superuser = True
    user.save()


def _login_and_get_playwright_cookies(*, base_url: str, username: str, password: str) -> list[dict[str, Any]]:
    """
    Autentica via HTTP (requests) e devolve cookies compatíveis com Playwright.

    Motivo:
    - O runtime atual usa `SESSION_ENGINE = cache`, então criar SessionStore manual no DB não garante login.
    - Login real via /login/funcionario/ é a fonte de verdade do cookie de sessão.
    """
    import requests

    parsed = urlparse(base_url)
    if not parsed.hostname:
        raise SystemExit(f"Invalid base_url: {base_url}")

    login_url = base_url.rstrip("/") + "/login/funcionario/"
    s = requests.Session()
    r = s.get(login_url, timeout=20)
    r.raise_for_status()

    csrf = None
    m = re.search(r"name=['\"]csrfmiddlewaretoken['\"]\s+value=['\"]([^'\"]+)['\"]", r.text)
    if m:
        csrf = m.group(1)

    payload: dict[str, str] = {"username": username, "password": password, "next": "/dashboard/"}
    if csrf:
        payload["csrfmiddlewaretoken"] = csrf

    resp = s.post(
        login_url,
        data=payload,
        headers={"Referer": login_url},
        allow_redirects=False,
        timeout=20,
    )
    if resp.status_code not in (200, 302):
        raise SystemExit(f"Login failed: {resp.status_code}")

    cookies: list[dict[str, Any]] = []
    for c in s.cookies:
        cookies.append(
            {
                "name": c.name,
                "value": c.value,
                "domain": parsed.hostname,
                "path": "/",
                "httpOnly": True,
                "secure": parsed.scheme == "https",
                "sameSite": "Lax",
            }
        )
    if not any(c["name"] == "sessionid" for c in cookies):
        raise SystemExit("Login did not yield a sessionid cookie.")
    return cookies


def _safe_filename(path: str) -> str:
    if path == "/":
        return "home"
    return _slugify(path.strip("/"))


def _run_smoke(
    *,
    base_url: str,
    out_dir: str,
    breakpoints: list[Breakpoint],
    targets: list[str],
    username: str,
    password: str,
) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    os.makedirs(out_dir, exist_ok=True)

    results: list[dict[str, Any]] = []
    started_at = _dt.datetime.now().isoformat(timespec="seconds")

    # Public-only pages: we want to snapshot them without being redirected by an auth session.
    public_only = {"/login/", "/login/funcionario/", "/logout/"}

    auth_cookies = _login_and_get_playwright_cookies(base_url=base_url, username=username, password=password)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for bp in breakpoints:
            ctx_dir = os.path.join(out_dir, f"{bp.label}_{bp.width}x{bp.height}")
            os.makedirs(ctx_dir, exist_ok=True)

            auth_ctx = browser.new_context(
                locale="pt-BR",
                viewport={"width": bp.width, "height": bp.height},
                is_mobile=bp.is_mobile,
                has_touch=True,
                device_scale_factor=bp.device_scale_factor,
                user_agent=(
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                    "Version/17.0 Mobile/15E148 Safari/604.1"
                    if bp.is_mobile
                    else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            auth_ctx.add_cookies(auth_cookies)

            public_ctx = browser.new_context(
                locale="pt-BR",
                viewport={"width": bp.width, "height": bp.height},
                is_mobile=bp.is_mobile,
                has_touch=True,
                device_scale_factor=bp.device_scale_factor,
                user_agent=(
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                    "Version/17.0 Mobile/15E148 Safari/604.1"
                    if bp.is_mobile
                    else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
            )

            for path in targets:
                ctx = public_ctx if path in public_only else auth_ctx
                page = ctx.new_page()

                console_errors: list[str] = []
                page_errors: list[str] = []

                page.on(
                    "console",
                    lambda msg: console_errors.append(f"{msg.type}: {msg.text}") if msg.type in ("error", "warning") else None,
                )
                page.on("pageerror", lambda err: page_errors.append(str(err)))

                url = base_url.rstrip("/") + path
                nav_error: str | None = None
                status: int | None = None
                final_url: str | None = None

                try:
                    resp = page.goto(url, wait_until="load", timeout=45000)
                    final_url = page.url
                    if resp is not None:
                        status = resp.status
                except Exception as e:
                    nav_error = str(e)

                overflow = None
                try:
                    overflow = page.evaluate(
                        "() => {"
                        "  const root = document.documentElement;"
                        "  const vw = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);"
                        "  const sw = root.scrollWidth || 0;"
                        "  return { hasOverflow: sw > vw + 1, overflowPx: Math.max(0, sw - vw), vw, sw };"
                        "}"
                    )
                except Exception:
                    overflow = None

                title = None
                try:
                    title = page.title()
                except Exception:
                    title = None

                screenshot_name = f"{_safe_filename(path)}.png"
                screenshot_path = os.path.join(ctx_dir, screenshot_name)
                try:
                    # Viewport screenshot keeps mobile readability; full-page screenshots get too tiny.
                    page.screenshot(path=screenshot_path, full_page=False)
                except Exception:
                    screenshot_path = None

                results.append(
                    {
                        "breakpoint": dataclasses.asdict(bp),
                        "path": path,
                        "url": url,
                        "final_url": final_url,
                        "status": status,
                        "nav_error": nav_error,
                        "title": title,
                        "console_errors": console_errors[:50],
                        "page_errors": page_errors[:50],
                        "overflow": overflow,
                        "screenshot": screenshot_path,
                    }
                )
                page.close()

            auth_ctx.close()
            public_ctx.close()

        browser.close()

    finished_at = _dt.datetime.now().isoformat(timespec="seconds")
    payload = {
        "started_at": started_at,
        "finished_at": finished_at,
        "base_url": base_url,
        "out_dir": out_dir,
        "breakpoints": [dataclasses.asdict(b) for b in breakpoints],
        "targets": targets,
        "results": results,
    }
    with open(os.path.join(out_dir, "smoke_results.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return payload


def _summarize(payload: dict[str, Any], out_dir: str) -> str:
    rows = payload.get("results") or []

    def is_fail(r: dict[str, Any]) -> bool:
        status = r.get("status")
        nav_error = r.get("nav_error")
        if nav_error:
            return True
        if status is None:
            return True
        if status >= 500:
            return True
        return False

    def is_warn(r: dict[str, Any]) -> bool:
        status = r.get("status")
        if status in (401, 403, 404, 405):
            return True
        overflow = r.get("overflow") or {}
        if overflow and overflow.get("hasOverflow"):
            return True
        if r.get("console_errors") or r.get("page_errors"):
            return True
        return False

    total = len(rows)
    fails = [r for r in rows if is_fail(r)]
    warns = [r for r in rows if (not is_fail(r)) and is_warn(r)]

    md_lines = []
    md_lines.append(f"# Smoke visual mobile (auto) — {_dt.date.today().isoformat()}")
    md_lines.append("")
    md_lines.append(f"- base: `{payload.get('base_url')}`")
    md_lines.append(f"- output: `{out_dir}`")
    md_lines.append(f"- páginas testadas (visitas totais = rota x breakpoint): `{total}`")
    md_lines.append(f"- FAIL: `{len(fails)}`")
    md_lines.append(f"- WARN: `{len(warns)}`")
    md_lines.append("")
    md_lines.append("## Achados (FAIL/WARN)")
    md_lines.append("")
    md_lines.append("| severidade | breakpoint | path | status | overflow | erros | screenshot |")
    md_lines.append("| --- | --- | --- | --- | --- | --- | --- |")

    def overflow_cell(r: dict[str, Any]) -> str:
        o = r.get("overflow") or {}
        if not o:
            return ""
        if not o.get("hasOverflow"):
            return ""
        return f"{o.get('overflowPx')}px"

    def errors_cell(r: dict[str, Any]) -> str:
        c = len(r.get("console_errors") or [])
        p = len(r.get("page_errors") or [])
        if not (c or p):
            return ""
        return f"console:{c} page:{p}"

    def sev(r: dict[str, Any]) -> str:
        return "FAIL" if is_fail(r) else "WARN"

    for r in (fails + warns):
        bp = r.get("breakpoint") or {}
        bp_label = bp.get("label") or f"{bp.get('width')}x{bp.get('height')}"
        sc = r.get("screenshot")
        md_lines.append(
            "| {sev} | `{bp}` | `{path}` | `{status}` | `{ov}` | `{errs}` | `{sc}` |".format(
                sev=sev(r),
                bp=bp_label,
                path=r.get("path") or "",
                status=r.get("status"),
                ov=overflow_cell(r),
                errs=errors_cell(r),
                sc=(sc or ""),
            )
        )

    md = "\n".join(md_lines).rstrip() + "\n"
    report_path = os.path.join(out_dir, "smoke_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md)
    return report_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=os.environ.get("BASE_URL", "http://127.0.0.1:8005"))
    parser.add_argument("--out", default=os.environ.get("SMOKE_OUT", os.path.join("tmp", "smoke_visual_mobile")))
    parser.add_argument("--password", default=os.environ.get("AUTO_PASS", "Aut0Test!"))
    args = parser.parse_args()

    # Ensure repo root is on sys.path even when running as tools\script.py.
    repo_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(repo_root))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django  # noqa: PLC0415

    django.setup()

    _ensure_autotest_user(password=args.password)

    breakpoints = [
        Breakpoint(label="mobile", width=390, height=844, is_mobile=True),
        Breakpoint(label="tablet", width=768, height=1024, is_mobile=False),
        Breakpoint(label="desktop", width=1280, height=800, is_mobile=False),
    ]

    base_paths = [
        "/",
        "/login/",
        "/login/funcionario/",
        "/acessos/",
        "/dashboard/",
        "/operacao/",
        "/operacao/owner/",
        "/operacao/manager/",
        "/operacao/recepcao/",
        "/operacao/coach/",
        "/operacao/dev/",
        "/operacao/whatsapp/",
        "/operacao/relatorios/",
        "/operacao/resumo-executivo/",
        "/operacao/wod/editor/",
        "/operacao/wod/paste/",
        "/operacao/wod/planner/",
        "/operacao/wod/templates/",
        "/operacao/wod/aprovacoes/",
        "/operacao/wod/historico/",
        "/entradas/",
        "/entradas/indice/",
        "/alunos/",
        "/alunos/novo/",
        "/alunos/balcao/",
        "/financeiro/",
        "/grade-aulas/",
        "/mapa-sistema/",
        "/configuracoes-operacionais/",
        "/configuracoes-operacionais/aluno/convites/",
        # Student app (best-effort; may redirect depending on auth)
        "/aluno/",
        "/aluno/onboarding/",
        "/aluno/grade/",
        "/aluno/wod/",
        "/aluno/rm/",
        "/aluno/configuracoes/",
        "/aluno/offline/",
        "/aluno/entrar-com-convite/",
        "/aluno/sem-box/",
    ]
    targets = _build_target_paths(base_paths)

    stamp = _dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_dir = os.path.join(args.out, stamp)
    payload = _run_smoke(
        base_url=args.base,
        out_dir=out_dir,
        breakpoints=breakpoints,
        targets=targets,
        username="autotest",
        password=args.password,
    )
    report_path = _summarize(payload, out_dir)

    print("done")
    print("report:", report_path)
    print("json:", os.path.join(out_dir, "smoke_results.json"))


if __name__ == "__main__":
    main()
