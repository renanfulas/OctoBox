import sys
import os

import paramiko

from scripts.ssh_hardening import build_hardened_ssh_client


HOST = os.environ.get("OCTOBOX_VPS_HOST", "129.121.47.167")
PORT = int(os.environ.get("OCTOBOX_VPS_PORT", "22022"))
USERNAME = os.environ.get("OCTOBOX_VPS_USER", "root")
PASSWORD = os.environ.get("OCTOBOX_VPS_PASSWORD")

REMOTE_SCRIPT = """set -e
export DEBIAN_FRONTEND=noninteractive

echo "== Baseline =="
uname -r
lsb_release -a || true
timedatectl || true

echo "== Packages =="
apt update
apt install -y fail2ban unattended-upgrades apt-listchanges curl ca-certificates

echo "== UFW =="
ufw allow 22022/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "== Fail2Ban =="
systemctl enable --now fail2ban
cat >/etc/fail2ban/jail.d/sshd.local <<'EOF'
[sshd]
enabled = true
port = 22022
backend = systemd
maxretry = 5
findtime = 10m
bantime = 1h
EOF
systemctl restart fail2ban

echo "== Unattended Upgrades =="
cat >/etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF
systemctl enable unattended-upgrades || true
systemctl restart unattended-upgrades || true

echo "== SSH Safety Check =="
sshd -t
systemctl restart ssh
systemctl is-active ssh

echo "== Final Status =="
ufw status verbose
systemctl --no-pager --full status fail2ban | sed -n '1,40p'
systemctl --no-pager --full status unattended-upgrades | sed -n '1,40p'
ss -tulpn | grep 22022 || true
"""


def main() -> int:
    if not PASSWORD:
        print("Defina a variavel de ambiente OCTOBOX_VPS_PASSWORD antes de executar.", file=sys.stderr)
        return 2

    client = build_hardened_ssh_client()
    try:
        client.connect(
            HOST,
            port=PORT,
            username=USERNAME,
            password=PASSWORD,
            timeout=20,
            look_for_keys=False,
            allow_agent=False,
        )
    except Exception as exc:
        print(f"Falha ao conectar em {HOST}:{PORT}: {exc}", file=sys.stderr)
        return 1

    try:
        stdin, stdout, stderr = client.exec_command(
            f"bash -s <<'__CODEX_REMOTE_SCRIPT__'\n{REMOTE_SCRIPT}\n__CODEX_REMOTE_SCRIPT__\n"
        )  # nosec B601
        exit_status = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        if out:
            print(out)
        if err:
            print(err, file=sys.stderr)
        return exit_status
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
