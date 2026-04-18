import os
import secrets
import sys
from pathlib import Path

import paramiko

from scripts.ssh_hardening import build_hardened_ssh_client

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


HOST = os.environ.get("OCTOBOX_VPS_HOST", "129.121.47.167")
PORT = int(os.environ.get("OCTOBOX_VPS_PORT", "22022"))
USERNAME = os.environ.get("OCTOBOX_VPS_USER", "root")
PASSWORD = os.environ.get("OCTOBOX_VPS_PASSWORD")
DOMAIN = os.environ.get("OCTOBOX_DOMAIN", "app.octoboxfit.com.br")
REPO = os.environ.get("OCTOBOX_REPO", "https://github.com/renanfulas/OctoBox.git")
BRANCH = os.environ.get("OCTOBOX_BRANCH", "main")

BOOTSTRAP_PATH = Path(__file__).with_name("linux").joinpath("bootstrap_hostgator_octobox.sh")


def require_password() -> str:
    if not PASSWORD:
        print("Defina OCTOBOX_VPS_PASSWORD antes de executar.", file=sys.stderr)
        raise SystemExit(2)
    return PASSWORD


def generated(name: str) -> str:
    value = os.environ.get(name)
    if value:
        return value
    if name == "OCTOBOX_ADMIN_PATH":
        return f"painel-{secrets.token_urlsafe(16).replace('-', '').replace('_', '')[:24]}"
    return secrets.token_urlsafe(48)


def build_remote_command(script: str) -> str:
    secret_key = generated("OCTOBOX_SECRET_KEY")
    blind_index_key = generated("OCTOBOX_PHONE_BLIND_INDEX_KEY")
    admin_path = generated("OCTOBOX_ADMIN_PATH")
    db_password = generated("OCTOBOX_DB_PASSWORD")
    runtime_slug = os.environ.get("OCTOBOX_RUNTIME_SLUG", "octoboxfit-production")
    manager_enabled = os.environ.get("OCTOBOX_MANAGER_ENABLED", "True")

    env_lines = [
        f"export OCTOBOX_DOMAIN='{DOMAIN}'",
        f"export OCTOBOX_REPO='{REPO}'",
        f"export OCTOBOX_BRANCH='{BRANCH}'",
        f"export OCTOBOX_DB_PASSWORD='{db_password}'",
        f"export OCTOBOX_SECRET_KEY='{secret_key}'",
        f"export OCTOBOX_PHONE_BLIND_INDEX_KEY='{blind_index_key}'",
        f"export OCTOBOX_ADMIN_PATH='{admin_path}'",
        f"export OCTOBOX_RUNTIME_SLUG='{runtime_slug}'",
        f"export OCTOBOX_MANAGER_ENABLED='{manager_enabled}'",
    ]
    prelude = "\n".join(env_lines)
    return (
        f"{prelude}\n"
        "bash -s <<'__CODEX_HOSTGATOR_BOOTSTRAP__'\n"
        f"{script}\n"
        "__CODEX_HOSTGATOR_BOOTSTRAP__\n"
    )


def main() -> int:
    require_password()
    script = BOOTSTRAP_PATH.read_text(encoding="utf-8")
    remote_command = build_remote_command(script)

    client = build_hardened_ssh_client()
    client.connect(
        HOST,
        port=PORT,
        username=USERNAME,
        password=PASSWORD,
        timeout=20,
        look_for_keys=False,
        allow_agent=False,
    )

    try:
        stdin, stdout, stderr = client.exec_command(remote_command, get_pty=True)  # nosec B601
        for line in iter(stdout.readline, ""):
            sys.stdout.write(line)
            sys.stdout.flush()
        err = stderr.read().decode("utf-8", errors="replace")
        if err:
            sys.stderr.write(err)
            sys.stderr.flush()
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("\nBootstrap remoto concluido.")
            print("Segredos e env final em: /srv/octobox/shared/octobox.env")
            print("Superuser manual: sudo -u octobox bash -lc 'cd /srv/octobox/app && set -a && source /srv/octobox/shared/octobox.env && set +a && /srv/octobox/venv/bin/python manage.py createsuperuser'")
        return exit_status
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
