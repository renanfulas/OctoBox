import os
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
RCLONE_REMOTE_NAME = os.environ.get("OCTOBOX_RCLONE_REMOTE_NAME", "r2")
R2_ACCOUNT_ID = os.environ.get("OCTOBOX_R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.environ.get("OCTOBOX_R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.environ.get("OCTOBOX_R2_SECRET_ACCESS_KEY", "")
R2_BUCKET = os.environ.get("OCTOBOX_R2_BUCKET", "octobox-backups")
BACKUP_REMOTE_PREFIX = os.environ.get("OCTOBOX_BACKUP_REMOTE_PREFIX", "octoboxfit-production")
BACKUP_RETENTION_DAYS = os.environ.get("OCTOBOX_BACKUP_RETENTION_DAYS", "30")
BACKUP_MAX_AGE_HOURS = os.environ.get("OCTOBOX_BACKUP_MAX_AGE_HOURS", "36")
RUNTIME_DISK_THRESHOLD = os.environ.get("OCTOBOX_RUNTIME_DISK_THRESHOLD", "85")
ALERT_WEBHOOK_URL = os.environ.get("OCTOBOX_ALERT_WEBHOOK_URL", "")

SETUP_SCRIPT_PATH = Path(__file__).with_name("linux").joinpath("setup_r2_backup.sh")


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def main() -> int:
    if not PASSWORD:
        print("Defina OCTOBOX_VPS_PASSWORD antes de executar.", file=sys.stderr)
        return 2

    required = {
        "OCTOBOX_R2_ACCOUNT_ID": R2_ACCOUNT_ID,
        "OCTOBOX_R2_ACCESS_KEY_ID": R2_ACCESS_KEY_ID,
        "OCTOBOX_R2_SECRET_ACCESS_KEY": R2_SECRET_ACCESS_KEY,
        "OCTOBOX_R2_BUCKET": R2_BUCKET,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        print(f"Faltam variaveis obrigatorias: {', '.join(missing)}", file=sys.stderr)
        return 2

    script = SETUP_SCRIPT_PATH.read_text(encoding="utf-8")
    backup_remote = f"{RCLONE_REMOTE_NAME}:{R2_BUCKET}"
    env_lines = [
        f"export OCTOBOX_DOMAIN={shell_quote(DOMAIN)}",
        f"export OCTOBOX_RCLONE_REMOTE_NAME={shell_quote(RCLONE_REMOTE_NAME)}",
        f"export OCTOBOX_R2_ACCOUNT_ID={shell_quote(R2_ACCOUNT_ID)}",
        f"export OCTOBOX_R2_ACCESS_KEY_ID={shell_quote(R2_ACCESS_KEY_ID)}",
        f"export OCTOBOX_R2_SECRET_ACCESS_KEY={shell_quote(R2_SECRET_ACCESS_KEY)}",
        f"export OCTOBOX_R2_BUCKET={shell_quote(R2_BUCKET)}",
        f"export OCTOBOX_BACKUP_REMOTE={shell_quote(backup_remote)}",
        f"export OCTOBOX_BACKUP_REMOTE_PREFIX={shell_quote(BACKUP_REMOTE_PREFIX)}",
        f"export OCTOBOX_BACKUP_RETENTION_DAYS={shell_quote(BACKUP_RETENTION_DAYS)}",
        f"export OCTOBOX_BACKUP_MAX_AGE_HOURS={shell_quote(BACKUP_MAX_AGE_HOURS)}",
        f"export OCTOBOX_RUNTIME_DISK_THRESHOLD={shell_quote(RUNTIME_DISK_THRESHOLD)}",
        f"export OCTOBOX_ALERT_WEBHOOK_URL={shell_quote(ALERT_WEBHOOK_URL)}",
    ]
    remote_command = (
        "\n".join(env_lines)
        + "\n"
        + "bash -s <<'__CODEX_R2_SETUP__'\n"
        + script
        + "\n__CODEX_R2_SETUP__\n"
    )

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
        return stdout.channel.recv_exit_status()
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
