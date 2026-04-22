# Protocolo Renanfulas

Este diretório contém artefatos que implementam o *Protocolo Renanfulas* — regras de engajamento para o agente automatizado.

Arquivos principais:

- `trava_state.json` — estado atual do nível de travas (1,2,3).
- `scripts/trava_ops.py` — utilitários para `backup`, `unlock`, `lock` e `status`.
- `scripts/red_beacon.py` — monitor pós-alteração que verifica rotas críticas e aciona o "Vertical Skybeam" se ocorrerem múltiplas falhas.
- `routes_list.txt` — rotas a serem verificadas pelo `red_beacon`.

Protocolos/observações:

- Antes de qualquer alteração programática em arquivos, o agente deve checar `trava_state.json` e obedecer as permissões descritas no seu pedido original.
- Alteração para Nível 3 exige confirmação explícita (interativa) e criação de snapshot via `git stash`.
- Em caso de detecção de 3+ rotas com erro após alteração, `red_beacon` pode reverter usando `git stash pop` e forçar retorno para Nível 1.

Executando comandos úteis:

```powershell
python .agents\scripts\trava_ops.py status
python .agents\scripts\trava_ops.py unlock 2
python .agents\scripts\trava_ops.py unlock 3   # requer confirmação interativa
python .agents\scripts\trava_ops.py backup
python .agents\scripts\red_beacon.py --routes-file .agents/routes_list.txt --base-url http://127.0.0.1:8000 --threshold 3 --revert
```

Use com cuidado: estes scripts executam `git stash` e `git stash pop` para snapshots e reverts automáticos.
