**Resumo das mudanças**
- Aumenta TTL de cache para contagens do shell e usa o setting configurável.

**Arquivos principais modificados**
- `config/settings/base.py`
- `access/shell_actions.py`

**Por que esta mudança é necessária**
- Reduz pressão no banco de dados para métricas globais (shell counts) em picos de uso.

**Como testar**
1. Verificar que `SHELL_COUNTS_CACHE_TTL_SECONDS` está definido no settings (ou usar default 60).
2. Reiniciar cache/backend e acessar páginas que exibem `shell_action_buttons` para validar contagens.

**Checklist**
- [ ] Removi arquivos sensíveis do repositório e purguei histórico se necessário.
- [ ] Adicionei entry no `CHANGELOG.md`.
