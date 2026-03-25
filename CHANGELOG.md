# Changelog

## Unreleased

### Security / Performance
- Aumenta TTL de cache para contagens do shell: `SHELL_COUNTS_CACHE_TTL_SECONDS` padrão de `15` → `60` segundos.
- Uso do setting `SHELL_COUNTS_CACHE_TTL_SECONDS` em `access/shell_actions.py` para persistência do cache.

Files changed:
- `config/settings/base.py`
- `access/shell_actions.py`

Notes:
- Remova e rode `git rm --cached` para quaisquer bancos de dados ou backups acidentalmente versionados antes de abrir o PR.
