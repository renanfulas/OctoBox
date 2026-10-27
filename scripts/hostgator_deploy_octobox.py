"""Deprecated direct-SSH deploy entrypoint; kept to fail closed for old callers."""

import sys


def main() -> int:
    print(
        "Deploy/rollback direto por SSH foi desativado. Use o workflow "
        "VPS Deploy (Hostgator São Paulo) para publicar um SHA aprovado e o "
        "runbook operacional para rollback.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
