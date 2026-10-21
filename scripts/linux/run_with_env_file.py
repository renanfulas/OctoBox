#!/usr/bin/env python3
"""Execute a command with literal values loaded from an env file."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or any(character.isspace() for character in key):
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        values[key] = value
    return values


def main() -> int:
    if len(sys.argv) < 4 or sys.argv[2] != "--":
        print(
            "usage: run_with_env_file.py ENV_FILE -- COMMAND [ARG ...]",
            file=sys.stderr,
        )
        return 2

    env = os.environ.copy()
    env.update(parse_env_file(Path(sys.argv[1])))
    return subprocess.run(sys.argv[3:], env=env, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
