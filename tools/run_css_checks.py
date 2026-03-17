#!/usr/bin/env python3
"""
Run CSS linter + formatter helper (Python fallback).

Behavior:
- If `npm` is available it runs `npm run lint:css` then `npm run format:css`.
- If `npm` is missing and `docker` is available it runs the same commands
  inside a temporary `node:lts` container (mounts the repo into /work).
- Otherwise it prints installation instructions.

Usage: from the repo root run the project's Python interpreter, for example:
  .venv\Scripts\python.exe tools/run_css_checks.py
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
        docker_cmd = [
            'docker', 'run', '--rm', '-v', f"{mount}:/work", '-w', '/work',
            'node:lts', 'bash', '-lc', 'npm ci --silent && npm run lint:css && npm run format:css'
        ]
        return run(docker_cmd, repo_root)

    print('[run_css_checks] neither npm nor docker found on PATH')
    print('Install Node.js (LTS) from https://nodejs.org/ and then run:')
    print('  npm install --silent && npm run lint:css && npm run format:css')
    print('Or install Docker Desktop and re-run this script to use the container fallback.')
    return 2


if __name__ == '__main__':
    exit(main())
