"""
ARQUIVO: scanner de saude de rotas para o Red Beacon (.agents/scripts/red_beacon.py).

POR QUE ELE EXISTE:
- red_beacon.py referenciava este arquivo, mas ele nao existia no repositorio
  (SCANNER_PATH apontava para um caminho morto). O beacon falhava em silencio:
  subprocess sem output capturado, scan_output.json nunca criado, get_health()
  retornava None, e o beacon imprimia "Falha ao obter dados de saude" e seguia
  sem checar nada.

O QUE ESTE ARQUIVO FAZ:
1. Le uma lista de rotas relativas de um arquivo texto (uma por linha, # comenta).
2. Faz GET em cada rota contra um base-url, SEM seguir redirect (precisa ver o
   302/403 cru, nao a pagina de destino apos o redirect).
3. Escreve scan_output.json: lista de {route, status, detail}.

PONTOS CRITICOS:
- Sem dependencia externa (so stdlib) — nao exige instalar nada para rodar.
- NoRedirectHandler existe para o beacon enxergar 302 como 302, nao como 200
  da pagina de login pos-redirect.
- status=0 (nao um codigo HTTP real) significa falha de conexao — servidor
  fora do ar, endereco errado, timeout. O beacon trata isso como erro tambem
  (nao esta em {200,302,403}), o que e o comportamento correto.
- Este scanner faz GET anonimo. Ele NAO detecta regressao de autorizacao
  (ex.: 403 esperado virando 200 por engano) especificamente porque 403 e
  tratado como saudavel pelo beacon de proposito — rotas protegidas devem
  responder 403/302 sem sessao. Para checar authz de verdade, e preciso de
  teste com sessao autenticada, fora do escopo deste smoke scanner.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Impede o urllib de seguir redirect — precisamos do status 30x cru."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _read_routes(path: str) -> list[str]:
    routes = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            routes.append(line)
    return routes


def _probe(base_url: str, route: str, timeout: float) -> dict:
    url = base_url.rstrip('/') + route
    opener = urllib.request.build_opener(_NoRedirectHandler)
    req = urllib.request.Request(url, method='GET', headers={'User-Agent': 'octobox-red-beacon/1.0'})

    try:
        with opener.open(req, timeout=timeout) as resp:
            return {'route': route, 'status': resp.status, 'detail': ''}
    except urllib.error.HTTPError as exc:
        # Redirect (302/301) ou erro HTTP (403/404/500...) chegam aqui —
        # o NoRedirectHandler faz o urllib tratar redirect como "erro" para
        # nao seguir, mas o codigo em exc.code e o status real da resposta.
        return {'route': route, 'status': exc.code, 'detail': str(exc.reason)}
    except urllib.error.URLError as exc:
        # Servidor fora do ar, DNS falhou, timeout de conexao.
        return {'route': route, 'status': 0, 'detail': f'conexao falhou: {exc.reason}'}
    except Exception as exc:  # defensivo: nunca deixar uma rota derrubar o scan inteiro
        return {'route': route, 'status': 0, 'detail': f'erro inesperado: {exc}'}


def main() -> int:
    parser = argparse.ArgumentParser(description='Scanner de saude de rotas para o Red Beacon.')
    parser.add_argument('--routes-file', default='.agents/routes_list.txt')
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    parser.add_argument('--output', default='scan_output.json')
    parser.add_argument('--timeout', type=float, default=5.0)
    args = parser.parse_args()

    try:
        routes = _read_routes(args.routes_file)
    except OSError as exc:
        print(f'Falha ao ler {args.routes_file}: {exc}', file=sys.stderr)
        return 1

    results = [_probe(args.base_url, route, args.timeout) for route in routes]

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    ok = sum(1 for r in results if r['status'] in (200, 302, 403))
    print(f'scan_routes: {ok}/{len(results)} rotas OK (200/302/403). Saida: {args.output}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
