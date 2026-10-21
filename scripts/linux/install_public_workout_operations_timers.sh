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
  octobox-signal-mesh-retries
)
# Workers longos (sem timer): o aviso do fim do descanso precisa de 1-2 s de
# precisao, que a fila de 1 minuto nao entrega.
services=(
  octobox-public-workout-rest-alerts
)

for unit in "${units[@]}"; do
  install -m 0644 "${unit_dir}/${unit}.service" "${systemd_dir}/${unit}.service"
  install -m 0644 "${unit_dir}/${unit}.timer" "${systemd_dir}/${unit}.timer"
done

for unit in "${services[@]}"; do
  install -m 0644 "${unit_dir}/${unit}.service" "${systemd_dir}/${unit}.service"
done

systemctl daemon-reload
for unit in "${units[@]}"; do
  systemctl enable --now "${unit}.timer"
done
for unit in "${services[@]}"; do
  systemctl enable "${unit}.service"
  systemctl restart "${unit}.service"
done
systemctl --no-pager status "${services[@]/%/.service}" | head -n 20 || true
systemctl list-timers 'octobox-public-workout-*' 'octobox-signal-mesh-retries.timer' --no-pager
