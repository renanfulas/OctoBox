#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute como root." >&2
  exit 1
fi

repo_dir="${OCTOBOX_REPO_DIR:-/srv/octobox/app}"
unit_dir="${repo_dir}/infra/hostgator-vps/systemd"
systemd_dir="/etc/systemd/system"
units=(
  octobox-public-workout-outbox
  octobox-public-workout-operations
  octobox-public-workout-metrics
)

for unit in "${units[@]}"; do
  install -m 0644 "${unit_dir}/${unit}.service" "${systemd_dir}/${unit}.service"
  install -m 0644 "${unit_dir}/${unit}.timer" "${systemd_dir}/${unit}.timer"
done

systemctl daemon-reload
for unit in "${units[@]}"; do
  systemctl enable --now "${unit}.timer"
done
systemctl list-timers 'octobox-public-workout-*' --no-pager
