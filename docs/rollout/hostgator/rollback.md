<!-- FONTE DA VERDADE: scripts/linux/rollback_octobox.sh. -->

# Rollback — HostGator VPS

O rollback seleciona a release anterior completa registrada pelo deploy, valida
manifesto, venv e `manage.py check`, move `/srv/octobox/current` atomicamente,
reinicia Gunicorn e exige que o health confirme os SHAs publicado e carregado.
Se a validação falhar, tenta restaurar o ponteiro que estava ativo antes do
rollback e retorna falha explícita.

Ao restaurar o ponteiro após rollback malsucedido, reinicia também o worker
`octobox-public-workout-rest-alerts`, caso esteja instalado, para que ele carregue
a mesma release restaurada. Falha no restart gera alerta; verificar o worker no
host mesmo quando Gunicorn responde, pois o health HTTP não cobre esse processo.

```bash
sudo bash /srv/octobox/current/scripts/linux/rollback_octobox.sh
```

O script compartilha lock com o deploy. Não executa migrations reversas nem
restaura banco automaticamente: o schema vivo deve ser compatível com a release
anterior. Migrações precisam usar expansão e contração; para migration destrutiva,
parar antes da ativação e definir janela e plano de restore específico. O backup
pré-deploy fica registrado em `shared/deploy-state/last_backup_path`.

## Conferência

```bash
readlink -f /srv/octobox/current
cat /srv/octobox/shared/deploy-state/current_commit
curl --fail --silent https://app.octoboxfit.com.br/api/v1/health/
systemctl is-active octobox-gunicorn
```

O health precisa trazer `healthy=true`, `release_consistent=true` e igualdade
entre `deployed_sha` e `loaded_sha`. Depois rode o [smoke pós-deploy](smoke.md).
O layout de releases e as alterações dos serviços descritos neste runbook ainda
precisam ser ensaiados em homologação com sequência A → B → A antes de ativar em
produção.
