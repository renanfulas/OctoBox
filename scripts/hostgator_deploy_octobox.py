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
BRANCH = os.environ.get("OCTOBOX_BRANCH", "main")
ACTION = os.environ.get("OCTOBOX_ACTION", "deploy").strip().lower()

DEPLOY_SCRIPT_PATH = Path(__file__).with_name("linux").joinpath("deploy_octobox.sh")
ROLLBACK_SCRIPT_PATH = Path(__file__).with_name("linux").joinpath("rollback_octobox.sh")


def main() -> int:
    if not PASSWORD:
        print("Defina OCTOBOX_VPS_PASSWORD antes de executar.", file=sys.stderr)
        return 2

    if ACTION == "deploy":
        script = DEPLOY_SCRIPT_PATH.read_text(encoding="utf-8")
    elif ACTION == "rollback":
        script = ROLLBACK_SCRIPT_PATH.read_text(encoding="utf-8")
    else:
        print(f"ACTION invalida: {ACTION}. Use deploy ou rollback.", file=sys.stderr)
        return 2
    remote_command = (
        f"export OCTOBOX_DOMAIN='{DOMAIN}'\n"
        f"export OCTOBOX_BRANCH='{BRANCH}'\n"
        "bash -s <<'__CODEX_RELEASE__'\n"
        f"{script}\n"
        "__CODEX_RELEASE__\n"
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
