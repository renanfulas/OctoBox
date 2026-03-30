"""
ARQUIVO: carregador simples de variaveis de ambiente do projeto.

POR QUE ELE EXISTE:
- Permite ler `.env` e `.env.test` sem depender de bibliotecas externas.
- Centraliza a regra para que manage.py, settings e outros entrypoints usem o mesmo comportamento.

O QUE ESTE ARQUIVO FAZ:
1. Faz parse simples de linhas `CHAVE=valor`.
2. Carrega arquivos `.env` opcionais sem sobrescrever variaveis do sistema por acidente.
3. Permite que `.env.test` complemente ou sobreponha apenas valores vindos do `.env`.

PONTOS CRITICOS:
- Este parser e propositalmente simples e cobre o formato usado pelo projeto.
- Ele nao substitui um gerenciador de segredos de producao.
- Mudancas aqui afetam qualquer ponto que inicialize o ambiente do Django.
"""

from __future__ import annotations

import os
from pathlib import Path


def _parse_env_line(raw_line: str):
    line = raw_line.strip()
    if not line or line.startswith('#'):
        return None

    if line.startswith('export '):
        line = line[len('export '):].strip()

    if '=' not in line:
        return None

    key, value = line.split('=', 1)
    key = key.strip()
    value = value.strip()

    if not key or any(char.isspace() for char in key):
        return None

    if value and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    elif ' #' in value:
        value = value.split(' #', 1)[0].rstrip()

    return key, value


def load_env_file(path, *, protected_keys=None, override=False):
    env_path = Path(path)
    loaded_keys = set()
    protected_keys = set(protected_keys or ())

    if not env_path.exists() or not env_path.is_file():
        return loaded_keys

    for raw_line in env_path.read_text(encoding='utf-8').splitlines():
        parsed = _parse_env_line(raw_line)
        if not parsed:
            continue

        key, value = parsed

        if key in os.environ and (not override or key in protected_keys):
            continue

        os.environ[key] = value
        loaded_keys.add(key)

    return loaded_keys


def load_project_env(base_dir, *, include_test_file=False):
    project_root = Path(base_dir)
    protected_keys = set(os.environ.keys())

    loaded_from_default = load_env_file(project_root / '.env')

    if include_test_file:
        load_env_file(
            project_root / '.env.test',
            protected_keys=protected_keys,
            override=True,
        )

    return loaded_from_default
