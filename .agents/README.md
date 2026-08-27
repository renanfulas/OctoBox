# Protocolo Renanfulas

Este diretório contém artefatos que implementam o *Protocolo Renanfulas* — regras de engajamento para o agente automatizado.

Arquivos principais:

- `trava_state.json` — estado atual do nível de travas (1,2,3).
- `scripts/trava_ops.py` — utilitários para `backup`, `revert`, `unlock`, `lock` e `status`.
- `scripts/red_beacon.py` — monitor pós-alteração que verifica rotas críticas e aciona o "Vertical Skybeam" se ocorrerem `--threshold` ou mais falhas.
- `scan_routes.py` (raiz do repo) — scanner que o `red_beacon` chama. GET anônimo em cada rota, sem seguir redirect, escreve `scan_output.json`.
- `routes_list.txt` — rotas a serem verificadas pelo `red_beacon`.

## Correções de 2026-08-25

Três defeitos achados e corrigidos nesta data — documentados aqui para não se repetirem:

1. **`scan_routes.py` não existia.** `red_beacon.py` referenciava um caminho morto; o scan falhava em silêncio (`get_health()` retornava `None`, imprimia "Falha ao obter dados de saúde" e seguia sem checar nada). Criado.
2. **`> $null 2>&1` era sintaxe de PowerShell dentro de um `subprocess.run(shell=True)`**, que no Windows invoca `cmd.exe`. Em vez de descartar a saída, criava um arquivo literalmente chamado `$null` no diretório atual. Trocado por chamadas de `subprocess.run` com lista de argumentos (sem `shell=True`, sem redirecionamento de shell — portátil entre Windows e POSIX).
3. **`git stash push` / `git stash pop` tinham semântica invertida para o caso de uso.** `push` *remove* as mudanças da working tree (fazia backup e desfazimento ao mesmo tempo) e empilha sobre a pilha de stash **compartilhada do usuário** — um `pop` cego no revert atingiria qualquer stash pré-existente do desenvolvedor, não necessariamente o backup do protocolo. Trocado por `git stash create` + `git stash store`: cria um snapshot referenciado por **hash específico** (nunca por índice `stash@{N}`, que desloca a cada `git stash` novo), sem tocar a working tree e sem mexer em nenhuma entrada alheia da pilha.

**Limitação que continua existindo, documentada em vez de escondida:** o snapshot via `git stash create` não captura arquivos **não rastreados** (novos). Depois de um `trava_ops.py revert`, rode `git status` — arquivos novos criados durante a janela de nível 3 sobrevivem ao revert e precisam de limpeza manual. Deliberadamente **não** usamos `git clean` para resolver isso — apagaria arquivos da sessão sem confirmação.

**Limitação do `red_beacon` que continua existindo:** é um scanner GET anônimo. Ele prova "a rota resolve sem 500", não "a autorização está correta" — `403` é tratado como saudável de propósito, porque rota protegida deve responder `403`/`302` sem sessão. Uma regressão que deveria bloquear e passa a liberar **não é pega** por este beacon. Ver comentário no topo de `routes_list.txt`.

Protocolos/observações:

- Antes de qualquer alteração programática em arquivos, o agente deve checar `trava_state.json` e obedecer as permissões descritas no seu pedido original.
- Alteração para Nível 3 exige confirmação explícita (interativa) e criação de snapshot via `trava_ops.py backup` (chamado automaticamente pelo `unlock 3`).
- Em caso de detecção de `--threshold` ou mais rotas com erro após alteração, `red_beacon --revert` reverte via `trava_ops.py revert` e trava para Nível 1. **Sem `--revert`, o beacon só alerta — nunca mexe em git nem no nível.**

Executando comandos úteis:

```powershell
python .agents\scripts\trava_ops.py status
python .agents\scripts\trava_ops.py unlock 2
python .agents\scripts\trava_ops.py unlock 3   # requer confirmação interativa, cria snapshot
python .agents\scripts\trava_ops.py backup     # snapshot manual, sem mudar nível
python .agents\scripts\trava_ops.py revert     # restaura o ultimo backup_ref registrado
python .agents\scripts\red_beacon.py --routes-file .agents/routes_list.txt --base-url http://127.0.0.1:8000 --threshold 3 --revert
```

Use com cuidado: `revert` descarta mudanças em arquivos rastreados (`git checkout -- .`) antes de reaplicar o snapshot. Confira `git status` antes de rodar se não tiver certeza do que está pendente.
