## Verificações e correções de CSS

Este documento descreve como rodar o linter e o formatter de CSS localmente no projeto.

1) Usando Node/npm (recomendado)

- Instale Node.js LTS: https://nodejs.org/
- No diretório do projeto rode (uma vez):

```powershell
npm install --silent
```

- Para checar (stylelint):

```powershell
npm run lint:css
```

- Para aplicar correções automáticas (stylelint --fix):

```powershell
npm run format:css
```

2) Uso via PowerShell helper (detecta npm ou usa Docker como fallback)

- Script: `tools/run-css-checks.ps1`
- Execute no PowerShell a partir da raiz do repositório:

```powershell
.\tools\run-css-checks.ps1
```

3) Uso via Python helper (roda via venv Python)

- Se você usa a venv do projeto, execute:

```powershell
.venv\Scripts\python.exe tools/run_css_checks.py
```

- O helper Python detecta `npm` e, se não existir, tenta usar `docker` com a imagem `node:lts`.

4) Se não tiver `npm` nem `docker`

- Instale um deles. Recomenda-se Node.js LTS para desenvolvimento local.

5) Verificador rápido em Python (substituto mínimo quando stylelint não está disponível)

- Script: `tools/css_quick_lint.py`
- Ele faz checagens sintáticas básicas (chaves, parênteses, comentários e aspas) e pode ser útil para detectar erros que quebram o build.

6) Observações

- Evite editar arquivos dentro de `.venv/` — o helper `css_quick_lint.py` foi ajustado para evitar falsos-positivos nesses arquivos.
- Se quiser que eu rode os checks em CI, posso adicionar um job no pipeline que execute `npm run lint:css`.
