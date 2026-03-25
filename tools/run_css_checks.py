#!/usr/bin/env python3
"""
ARQUIVO: utilitário para lint e format de CSS via Python.

POR QUE ELE EXISTE:
- Permite rodar lint e formatador de CSS mesmo sem npm instalado, usando fallback Python ou Docker.

O QUE ESTE ARQUIVO FAZ:
1. Detecta se npm está disponível e executa lint/format CSS via scripts npm.
2. Se npm não está disponível, tenta rodar os comandos em um container Docker node:lts.
3. Exibe instruções de instalação caso nenhum método esteja disponível.

PONTOS CRÍTICOS:
- Falhas aqui podem impedir a padronização visual do CSS do projeto.
- Mudanças podem impactar pipelines de CI e desenvolvedores sem npm local.
"""
from __future__ import annotations
import os
import shutil
import subprocess
import sys
from pathlib import Path


def has_cmd(name: str) -> bool:
    return shutil.which(name) is not None


def run(cmd, cwd: Path) -> int:
    print(f"[run_css_checks] running: {' '.join(cmd)} (cwd={cwd})")
    proc = subprocess.run(cmd, cwd=str(cwd))
    print(f"[run_css_checks] exit: {proc.returncode}")
    return proc.returncode


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent

    if has_cmd('npm'):
        print('[run_css_checks] npm detected — running lint and format via npm scripts')
        code = run(['npm', 'run', 'lint:css'], repo_root)
        if code != 0:
            print('[run_css_checks] stylelint failed — fix issues or run formatter after addressing problems')
            return code
        return run(['npm', 'run', 'format:css'], repo_root)

    if has_cmd('docker'):
        print('[run_css_checks] npm not found — docker detected, using node:lts container')
        mount = str(repo_root).replace('\\', '/')
        # Use discrete command execution to avoid shell injection (Epic 8)
        docker_cmd = [
            'docker', 'run', '--rm', '-v', f"{mount}:/work", '-w', '/work',
            'node:lts', 'bash', '-c', 'npm ci --silent && npm run lint:css && npm run format:css'
        ]
        return run(docker_cmd, repo_root)

    print('[run_css_checks] neither npm nor docker found on PATH')
    print('Install Node.js (LTS) from https://nodejs.org/ and then run:')
    print('  npm install --silent && npm run lint:css && npm run format:css')
    print('Or install Docker Desktop and re-run this script to use the container fallback.')
    return 2


if __name__ == '__main__':
    exit(main())
