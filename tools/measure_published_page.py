"""
ARQUIVO: script de inspecao controlada para pagina publicada.

POR QUE ELE EXISTE:
- mede o website publicado com a mesma regua que usamos no ambiente local.
- ajuda a separar custo de payload, custo da view e politica de cache/compressao.

O QUE ESTE ARQUIVO FAZ:
1. acessa uma URL publicada, opcionalmente autenticando via login Django.
2. mede tempo observado de resposta e tamanho do HTML retornado.
3. extrai `current_page_behavior` e seus tempos internos quando presentes.
4. imprime um JSON pronto para comparar local x website.

PONTOS CRITICOS:
- para paginas autenticadas, o login depende do formulario padrao do Django com CSRF.
- o script privilegia `gzip, deflate` para podermos medir corpo comprimido sem ambiguidade.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
import time
import urllib.parse
import zlib
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared_support.published_page_probe import summarize_published_html_probe


def _extract_csrf_token(html: str) -> str | None:
    match = re.search(r'name=["\']csrfmiddlewaretoken["\']\s+value=["\']([^"\']+)["\']', html)
    if match:
        return match.group(1)
    return None


def _decode_response_body(body: bytes, *, content_encoding: str | None, fallback_encoding: str | None) -> str:
    normalized = (content_encoding or "").lower().strip()
    decoded_bytes = body
    if normalized == "gzip":
        decoded_bytes = gzip.decompress(body)
    elif normalized == "deflate":
        try:
            decoded_bytes = zlib.decompress(body)
        except zlib.error:
            decoded_bytes = zlib.decompress(body, -zlib.MAX_WBITS)

    encoding = fallback_encoding or "utf-8"
    return decoded_bytes.decode(encoding, errors="replace")


def _perform_stream_get(
    session: requests.Session,
    url: str,
    *,
    timeout: float,
    verify: bool,
) -> tuple[requests.Response, bytes, float]:
    started_at = time.perf_counter()
    response = session.get(
        url,
        allow_redirects=True,
        timeout=timeout,
        verify=verify,
        stream=True,
        headers={"Accept-Encoding": "gzip, deflate"},
    )
    response.raw.decode_content = False
    body = response.raw.read()
    elapsed_ms = (time.perf_counter() - started_at) * 1000
    return response, body, elapsed_ms


def _login_if_requested(
    session: requests.Session,
    *,
    login_url: str | None,
    username: str | None,
    password: str | None,
    timeout: float,
    verify: bool,
    next_path: str | None,
) -> None:
    if not login_url or not username:
        return

    login_page = session.get(login_url, timeout=timeout, verify=verify, headers={"Accept-Encoding": "gzip, deflate"})
    login_page.raise_for_status()
    csrf_token = _extract_csrf_token(login_page.text)
    payload = {
        "username": username,
        "password": password or "",
    }
    if csrf_token:
        payload["csrfmiddlewaretoken"] = csrf_token
    if next_path:
        payload["next"] = next_path

    headers = {"Referer": login_url}
    response = session.post(login_url, data=payload, headers=headers, timeout=timeout, verify=verify, allow_redirects=True)
    response.raise_for_status()


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mede payload, tempos e headers de uma pagina publicada do OctoBox.")
    parser.add_argument("url", help="URL completa da pagina que sera medida.")
    parser.add_argument("--login-url", help="URL completa da pagina de login Django.")
    parser.add_argument("--username", help="Usuario para autenticar antes da medicao.")
    parser.add_argument("--password", help="Senha do usuario.")
    parser.add_argument(
        "--next-path",
        help="Valor do campo next no login. Se omitido, usa o path da URL alvo.",
    )
    parser.add_argument(
        "--session-cookie",
        help="Valor de um cookie sessionid ja valido. Quando informado, ignora o login por formulario.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Timeout em segundos por request. Padrao: 30.",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Desliga verificacao TLS. Use so em homologacao controlada.",
    )
    parser.add_argument(
        "--output",
        help="Caminho opcional para salvar o JSON da medicao.",
    )
    return parser


def main() -> int:
    args = build_argument_parser().parse_args()
    verify = not args.insecure
    next_path = args.next_path or urllib.parse.urlsplit(args.url).path or "/"

    session = requests.Session()
    session.headers.update({"User-Agent": "OctoBoxPublishedPageProbe/1.0"})

    if args.session_cookie:
        parsed = urllib.parse.urlsplit(args.url)
        session.cookies.set("sessionid", args.session_cookie, domain=parsed.hostname, path="/")
    else:
        _login_if_requested(
            session,
            login_url=args.login_url,
            username=args.username,
            password=args.password,
            timeout=args.timeout,
            verify=verify,
            next_path=next_path,
        )

    response, encoded_body, elapsed_ms = _perform_stream_get(
        session,
        args.url,
        timeout=args.timeout,
        verify=verify,
    )
    response.raise_for_status()
    html = _decode_response_body(
        encoded_body,
        content_encoding=response.headers.get("Content-Encoding"),
        fallback_encoding=response.encoding,
    )
    summary = summarize_published_html_probe(
        url=response.url,
        status_code=response.status_code,
        html=html,
        headers=dict(response.headers),
        request_elapsed_ms=elapsed_ms,
        encoded_body_bytes=len(encoded_body),
    )

    rendered = json.dumps(summary, ensure_ascii=False, indent=2)
    print(rendered)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(rendered + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
