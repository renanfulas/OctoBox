"""
Script de análise de `pg_stat_statements` e slow logs para Postgres.
Gera um relatório Markdown com as top queries por total_time, mean_time e calls.

Uso:
  python load_tests/pg_stat_report.py --dsn "postgresql://user:pass@host:5432/dbname" --out report_pg_stat.md

Requer: psycopg2-binary
  pip install psycopg2-binary

Se não tiver pg_stat_statements habilitado, o script tenta ler slow log (caminho informado).
"""
import argparse
import os
import sys
import time
from datetime import datetime

try:
    import psycopg2
except Exception:
    psycopg2 = None


def query_pg_stat(dsn, limit=50):
    if not psycopg2:
        raise RuntimeError('psycopg2 não disponível. Instale com: pip install psycopg2-binary')
    conn = psycopg2.connect(dsn)
    cur = conn.cursor()
    cur.execute("SELECT queryid, query, calls, total_time, mean_time, rows FROM pg_stat_statements ORDER BY total_time DESC LIMIT %s", (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def parse_slow_log(path, limit=50):
    # Leitura simples: agrupa por query text (linha continuada não tratada sofisticadamente)
    if not os.path.exists(path):
        return []
    counts = {}
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # heurística: linha com 'duration: ' contém tempo e query segue na mesma linha ou nas próximas
            if 'duration:' in line and 'statement:' in line:
                # formato psql: duration: 123.456 ms  statement: SELECT ...
                try:
                    parts = line.split('statement:')
                    query = parts[1].strip()
                except Exception:
                    query = line
                counts[query] = counts.get(query, 0) + 1
    items = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [(None, q, c, None, None, None) for q, c in items]


def generate_markdown(report_path, rows, from_slow=False):
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('# Relatório pg_stat_statements - {}\n\n'.format(datetime.utcnow().isoformat() + 'Z'))
        if from_slow:
            f.write('Fonte: slow log\n\n')
            f.write('| Rank | Count | Query |\n')
            f.write('|-|-|-|\n')
            for idx, r in enumerate(rows, 1):
                _, query, calls, _, _, _ = r
                f.write('| {} | {} | {} |\n'.format(idx, calls, query.replace('|', '\\|')[:1000]))
            return

        f.write('Fonte: pg_stat_statements\n\n')
        f.write('| Rank | Calls | Total Time (ms) | Mean Time (ms) | Rows | Query |\n')
        f.write('|-|-|-|-|-|-|\n')
        for idx, r in enumerate(rows, 1):
            queryid, query, calls, total_time, mean_time, rows_count = r
            q = (query or '').replace('\n', ' ').replace('|', '\\|')[:1000]
            f.write('| {} | {} | {:.2f} | {:.2f} | {} | {} |\n'.format(idx, calls, total_time or 0.0, mean_time or 0.0, rows_count or 0, q))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dsn', help='Postgres DSN, ex: postgresql://user:pass@host:5432/dbname')
    parser.add_argument('--slow-log', help='Caminho do slow log, se não usar pg_stat_statements')
    parser.add_argument('--out', default='load_tests/report_pg_stat.md')
    parser.add_argument('--limit', type=int, default=50)
    args = parser.parse_args()

    rows = []
    if args.dsn and psycopg2:
        try:
            rows = query_pg_stat(args.dsn, limit=args.limit)
            generate_markdown(args.out, rows, from_slow=False)
            print('Relatório gerado em', args.out)
            return
        except Exception as e:
            print('Falha ao consultar pg_stat_statements:', e)
            # fallback para slow log se informado

    if args.slow_log:
        rows = parse_slow_log(args.slow_log, limit=args.limit)
        generate_markdown(args.out, rows, from_slow=True)
        print('Relatório (slow log) gerado em', args.out)
        return

    print('Nenhuma fonte válida especificada. Forneça --dsn ou --slow-log e instale psycopg2-binary se necessário.')

if __name__ == '__main__':
    main()
