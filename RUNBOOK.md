# OctoBox Operations Runbook (Manual de Operações) 📖

Este guia contém os procedimentos operacionais para manter o OctoBox seguro, performático e resiliente após o endurecimento (Hardening).

## 🛡️ Segurança e Segredos

### 1. Rotação de Chaves
- **DJANGO_SECRET_KEY**: Nunca use a chave padrão de desenvolvimento. No deploy, gere uma nova:
  ```bash
  python -c 'import secrets; print(secrets.token_urlsafe(50))'
  ```
- **ADMIN_INIT_PASSWORD**: Se precisar reinicializar o sistema via `/api/system/init`, verifique se o segredo no `.env` foi alterado após o primeiro uso.

### 2. Scanners de CI/CD
O projeto está configurado com GitHub Actions (`security-scanners.yml`) que rodam:
- **Bandit**: Análise estática do código em busca de vulnerabilidades (ex: injeção).
- **Pip-Audit**: Verifica se as bibliotecas no `requirements.txt` possuem falhas conhecidas (CVEs).
- **Safety**: Check complementar de segurança de dependências.

---

## 🚀 Performance e Escala

### 1. Monitoramento (APM)
- Ativamos o **Sentry** no `production.py`. Verifique o dashboard periodicamente em busca de:
  - **Slow Queries**: Logamos qualquer consulta > 200ms.
  - **Memory Spikes**: Monitore o worker do Celery durante imports grandes.

### 2. Celery e Workers
- O OctoBox usa Celery para processar imports de alunos.
- **Runbook de Alerta**: Se a fila de "Jobs Recentes" no Dashboard estiver travada, reinicie os workers:
  ```bash
  celery -A config worker -l info
  ```

---

## 💾 Backups e Recuperação (Incident Response)

### 1. Snapshot Manual
Para criar um snapshot de segurança antes de grandes mudanças:
```bash
python manage.py create_snapshot --label="pre-migration-001"
```

### 2. Restore de Emergência (Walkthrough)
1. Use o comando de restore com validação de Schema:
   ```bash
   python manage.py restore_snapshot path/to/backup.zip
   ```
2. Se houver erro de "Schema Drift", você precisará rodar `migrate` após o restore ou usar `--force` se tiver certeza da integridade.

---
*Gerado via Autopilot - OctoBox Fortress (Fase Final)*
