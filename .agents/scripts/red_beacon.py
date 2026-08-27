import argparse
import os
import sys
import json
import subprocess

# Mesmo motivo do trava_ops.py: prints com emoji quebram em console nao-UTF-8.
for _stream in (sys.stdout, sys.stderr):
    if getattr(_stream, 'encoding', '').lower() != 'utf-8':
        try:
            _stream.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

# Reutiliza o scanner de rotas limpo
SCANNER_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'scan_routes.py')
TRAVA_OPS = os.path.join(os.path.dirname(__file__), 'trava_ops.py')


def parse_args():
    parser = argparse.ArgumentParser(description='Red Beacon — monitor de saude pos-alteracao.')
    parser.add_argument('--routes-file', default=os.path.join(
        os.path.dirname(__file__), '..', 'routes_list.txt'))
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    parser.add_argument('--threshold', type=int, default=3,
                         help='Numero de rotas com erro que dispara o Vertical Skybeam.')
    parser.add_argument('--revert', action='store_true',
                         help='Se o threshold for atingido, reverte via trava_ops.py revert '
                              'e trava o nivel para 1. Sem esta flag, o beacon so ALERTA — '
                              'nunca mexe em git nem em trava_state.json.')
    parser.add_argument('--output', default='scan_output.json')
    return parser.parse_args()


def get_health(args):
    print("📡 Red Beacon: Escaneando rotas críticas...")
    # Lista de argumentos, sem shell=True: nada de redirecionamento de shell
    # (`> $null 2>&1` era sintaxe de PowerShell rodando sob cmd.exe — criava
    # um arquivo chamado literalmente "$null" em vez de descartar a saida).
    # Captura stderr para diagnostico em vez de engolir silenciosamente.
    result = subprocess.run(
        [sys.executable, SCANNER_PATH,
         '--routes-file', args.routes_file,
         '--base-url', args.base_url,
         '--output', args.output],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
    )
    if result.returncode != 0:
        print(f"⚠️ scan_routes.py falhou (exit {result.returncode}): {result.stderr.strip()}")

    if not os.path.exists(args.output):
        return None

    with open(args.output, 'r', encoding='utf-8') as f:
        data = json.load(f)

    errors = [d for d in data if d['status'] not in (200, 302, 403)]
    return errors


def trigger_skybeam(*, do_revert: bool):
    print("\n" + "!" * 60)
    print("☢️ VERTICAL SKYBEAM ATIVADO! ☢️")
    print("Muitos erros detectados pós-alteração. Infortúnio iminente.")
    print("!" * 60 + "\n")

    if not do_revert:
        print("⚠️ --revert não foi passado — o beacon está apenas ALERTANDO.")
        print("   Nada em git ou em trava_state.json foi tocado. Revise manualmente,")
        print("   ou rode de novo com --revert para reverter automaticamente.")
        sys.exit(1)

    print("Revertendo via trava_ops.py revert (snapshot registrado no unlock nivel 3)...")
    revert_res = subprocess.run(
        [sys.executable, TRAVA_OPS, 'revert'],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
    )
    print(revert_res.stdout.strip())
    if revert_res.returncode != 0:
        print(f"⚠️ Revert falhou: {revert_res.stderr.strip()}")
        print("   NÃO travando o nível — o estado pode estar inconsistente. Intervenção manual necessária.")
        sys.exit(2)

    subprocess.run(
        [sys.executable, TRAVA_OPS, 'lock'],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
    )
    sys.exit(1)


def main():
    args = parse_args()
    errors = get_health(args)

    if errors is None:
        print("❌ Falha ao obter dados de saúde — scan_output.json não foi criado.")
        sys.exit(1)

    error_count = len(errors)

    if error_count == 0:
        print("✅ Red Beacon: Sistema SAUDÁVEL. Nenhuma anomalia detectada.")
    elif error_count < args.threshold:
        print(f"🟡 Red Beacon ATIVO: {error_count} rota(s) com erro detectada(s)!")
        for e in errors:
            print(f"  - {e['route']}: status={e['status']} {e['detail']}")
        print("⚠️ Recomendado: Revisar alterações imediatamente.")
    else:
        for e in errors:
            print(f"  - {e['route']}: status={e['status']} {e['detail']}")
        trigger_skybeam(do_revert=args.revert)


if __name__ == "__main__":
    main()
