$ErrorActionPreference = 'Stop'

$hostName = '129.121.47.167'
$port = 22022
$user = 'root'

Write-Host "Detectando seu IP publico atual..."
$publicIp = (
    Invoke-RestMethod -Uri 'https://api.ipify.org?format=text' -TimeoutSec 15
).ToString().Trim()

if (-not $publicIp) {
    throw 'Nao foi possivel detectar o IP publico atual.'
}

Write-Host "IP detectado: $publicIp"
$securePassword = Read-Host "Digite a senha do usuario root" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
$plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)

try {
    $env:OCTOBOX_VPS_HOST = $hostName
    $env:OCTOBOX_VPS_PORT = "$port"
    $env:OCTOBOX_VPS_USER = $user
    $env:OCTOBOX_VPS_PASSWORD = $plainPassword
    $env:OCTOBOX_FAIL2BAN_ALLOW_IP = $publicIp

    @'
import os
import sys

import paramiko

host = os.environ["OCTOBOX_VPS_HOST"]
port = int(os.environ["OCTOBOX_VPS_PORT"])
username = os.environ["OCTOBOX_VPS_USER"]
password = os.environ["OCTOBOX_VPS_PASSWORD"]
allow_ip = os.environ["OCTOBOX_FAIL2BAN_ALLOW_IP"]

remote_script = f"""set -e
mkdir -p /etc/fail2ban/jail.d
cat >/etc/fail2ban/jail.d/ignoreip.local <<'EOF'
[DEFAULT]
ignoreip = 127.0.0.1/8 ::1 {allow_ip}
EOF
systemctl restart fail2ban
fail2ban-client set sshd unbanip {allow_ip} || true
echo "== IgnoreIP =="
fail2ban-client get sshd ignoreip
echo "== Jail Status =="
fail2ban-client status sshd
"""

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(
    host,
    port=port,
    username=username,
    password=password,
    timeout=20,
    look_for_keys=False,
    allow_agent=False,
)

try:
    stdin, stdout, stderr = client.exec_command(
        f"bash -s <<'__CODEX_ALLOWLIST__'\n{remote_script}\n__CODEX_ALLOWLIST__\n"
    )
    exit_status = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    if out:
        print(out)
    if err:
        print(err, file=sys.stderr)
    raise SystemExit(exit_status)
finally:
    client.close()
'@ | py -
}
finally {
    if ($bstr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
    Remove-Item Env:OCTOBOX_VPS_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:OCTOBOX_FAIL2BAN_ALLOW_IP -ErrorAction SilentlyContinue
}
