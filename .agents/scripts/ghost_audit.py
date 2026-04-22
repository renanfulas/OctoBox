"""Ghost Audit: varredura de CSS hardcoded, N+1 heurístico e checagens de acessibilidade.
Gera um relatório JSON em `.agents/ghost_audit_report.json` e imprime resumo.

Uso:
  python .agents\scripts\ghost_audit.py --base-path . --report .agents/ghost_audit_report.json
"""
from pathlib import Path
import re
import json
import argparse

IGNORED_DIRS = {'.git', 'node_modules', '.venv', '.env', '.agents'}

STYLE_PROPS = {'margin', 'padding', 'color', 'font-size', 'display'}


def scan_templates(base):
    results = []
    ids = {}
    aria_issues = []
    for p in base.rglob('templates/**/*.html'):
        if any(part in IGNORED_DIRS for part in p.parts):
            continue
        text = p.read_text(encoding='utf-8', errors='ignore')
        # style="..."
        for m in re.finditer(r'style\s*=\s*"([^"]+)"', text, re.IGNORECASE):
            style = m.group(1)
            props = [s.strip().split(':')[0].strip() for s in style.split(';') if ':' in s]
            bad = [pr for pr in props if pr in STYLE_PROPS]
            if bad:
                results.append({'file': str(p.relative_to(base)), 'style': style, 'props': bad})
        # collect ids
        for m in re.finditer(r'id\s*=\s*"([^"]+)"', text):
            _id = m.group(1)
            ids.setdefault(_id, []).append(str(p.relative_to(base)))
        # aria checks for interactive elements
        for m in re.finditer(r'<(button|a|input|select|textarea)([^>]*)>', text, re.IGNORECASE):
            tag = m.group(1).lower(); attrs = m.group(2)
            if 'aria-' in attrs.lower() or 'aria' in attrs.lower() or 'title=' in attrs.lower():
                continue
            # input of type hidden skip
            if re.search(r'type\s*=\s*"hidden"', attrs, re.IGNORECASE):
                continue
            aria_issues.append({'file': str(p.relative_to(base)), 'tag': tag, 'snippet': m.group(0)[:200]})
    duplicate_ids = {k:v for k,v in ids.items() if len(v)>1}
    return {'style_inline': results, 'duplicate_ids': duplicate_ids, 'aria_issues': aria_issues}


def scan_backend(base):
    n_plus_one = []
    aggregates = []
    for p in base.rglob('**/*.py'):
        if any(part in IGNORED_DIRS for part in p.parts):
            continue
        if str(p).endswith('scripts\\ghost_audit.py'):
            continue
        text = p.read_text(encoding='utf-8', errors='ignore')
        lines = text.splitlines()
        # heuristic: for-loops with count() or exists() inside next 10 lines
        for i, line in enumerate(lines):
            if re.match(r'\s*for\s+', line):
                window = '\n'.join(lines[i:i+12])
                if re.search(r'\.count\s*\(|\.exists\s*\(', window):
                    n_plus_one.append({'file': str(p.relative_to(base)), 'line_no': i+1, 'snippet': lines[i].strip()})
                # detect attribute access that might be FK traversal
                if re.search(r'\.[a-zA-Z0-9_]+\.', window):
                    # simple heuristic: attribute dot access inside loop
                    n_plus_one.append({'file': str(p.relative_to(base)), 'line_no': i+1, 'snippet': lines[i].strip(), 'reason': 'attribute-access-in-loop'})
        # aggregates
        if re.search(r'\.aggregate\s*\(', text):
            # check naive cache usage
            if not re.search(r'cache\.|cache\(|@cache', text):
                aggregates.append({'file': str(p.relative_to(base)), 'note': 'aggregate without obvious cache usage'})
    return {'n_plus_one_candidates': n_plus_one, 'aggregates': aggregates}


def classify_report(rep):
    score = 0
    if rep['backend']['n_plus_one_candidates']:
        score += 3
    if rep['backend']['aggregates']:
        score += 2
    if rep['templates']['style_inline']:
        score += 1
    if rep['templates']['duplicate_ids']:
        score += 1
    if rep['templates']['aria_issues']:
        score += 2
    if score == 0:
        return '🟢 Limpo'
    if score <= 3:
        return '🟡 Alerta'
    return '🔴 Crítico'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-path', default='.', help='Caminho raiz do projeto')
    parser.add_argument('--report', default='.agents/ghost_audit_report.json')
    args = parser.parse_args()
    base = Path(args.base_path).resolve()

    templates = scan_templates(base)
    backend = scan_backend(base)

    report = {
        'templates': templates,
        'backend': backend,
        'summary': None
    }
    report['summary'] = classify_report(report)

    out = Path(args.report)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')

    print('\n--- Ghost Audit Summary ---')
    print('Resultado:', report['summary'])
    print('Templates: styles inline encontrados =', len(templates['style_inline']))
    print('Templates: ids duplicados =', len(templates['duplicate_ids']))
    print('Templates: issues de aria =', len(templates['aria_issues']))
    print('Backend: N+1 candidatos =', len(backend['n_plus_one_candidates']))
    print('Backend: aggregates sem cache =', len(backend['aggregates']))
    print('Relatório salvo em:', str(out))

if __name__ == '__main__':
    main()
