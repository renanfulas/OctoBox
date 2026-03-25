# Remover backups/snapshots do histórico Git e rotacionar segredos

Este guia descreve passos seguros para remover pastas de backups e arquivos de banco (ex.: `backups/`, `*.sqlite3`) do histórico Git e rotacionar segredos que possam ter vazado.

IMPORTANTE: essas operações reescrevem o histórico. Coordene com o time, faça backup do repositório atual e comunique que todos irão precisar re-clonar após o processo.

## 1) Fazer backup do repositório atual

No seu workstation ou servidor, faça um mirror para preservação antes de modificar o histórico:

```bash
git clone --mirror git@github.com:ORGA/REPO.git repo.git
cd repo.git
```

Substitua `git@github.com:ORGA/REPO.git` pela URL remota adequada.

## 2) Usar BFG Repo-Cleaner (recomendado pela simplicidade)

BFG é simples e resistente para remover arquivos/pastas grandes do histórico.

- Baixe BFG: https://rtyley.github.io/bfg-repo-cleaner/
- Execute (exemplo removendo `backups/` e arquivos `*.sqlite3`):

```bash
# dentro de repo.git (clone mirror)
java -jar /path/to/bfg.jar --delete-folders backups --delete-files "*.sqlite3" --no-blob-protection

# Depois executar limpeza final e compactação
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Forçar push para o remoto (ATENÇÃO: rewriting history)
git push --force
```

Observações:
- `--no-blob-protection` faz o BFG remover também blobs referenciados por tags/commits antigos; use com cuidado.
- Se quiser apenas remover arquivos maiores que X MB, o BFG fornece `--strip-blobs-bigger-than 100M`.

## 3) Alternativa: git-filter-repo (mais flexível)

`git-filter-repo` é a ferramenta recomendada atualmente pelo projeto Git para reescrita avançada (escreva paths/refs a remover). Se preferir `git-filter-repo`, siga a documentação oficial e teste em um clone mirror antes de executar o push forçado.

Exemplo conceitual (execute na mirror clone):

```bash
# instalar: pip install git-filter-repo
git clone --mirror git@github.com:ORGA/REPO.git repo.git
cd repo.git
# Consulte a doc oficial para o comando correto; teste antes de forçar push
git filter-repo --path backups/ --path-glob '*.sqlite3' --invert-paths
git push --force
```

> Nota: o `git-filter-repo` possui muitas opções; valide em um clone mirror e leia a documentação antes de usar em produção.

## 4) Rotacionar segredos e credenciais

Após reescrever o histórico, trate imediatamente os segredos que podem ter sido expostos:

- Rotacione quaisquer chaves/segredos/credentials que existam nos backups (DB, serviços terceiros, tokens de API).
- Troque senhas do banco de dados e revogue tokens/keys (ex.: Sentry, Stripe, AWS keys, etc.).
- Atualize variáveis no CI/CD e secret manager (GitHub Actions Secrets, Render/Vercel env, AWS Secrets Manager).

## 5) Comunicar time e instruções para colaboradores

Depois do `git push --force` todos os colaboradores devem re-clonar o repositório ou rebasear cuidadosamente. Recomende o passo mais seguro:

```bash
# opcao segura: re-clone
git clone git@github.com:ORGA/REPO.git

# ou, forçar reset no repositório local (perderá histórico local não-pushado)
git fetch origin
git reset --hard origin/main
```

## 6) Evitar reincidência

- Adicione `backups/` e padrões de snapshot ao `.gitignore`.
- Configure policy/branch protection no Git (evitar pushes diretos, exigir PRs e checks).
- Adicione varredura automática de segredos e políticas em CI: `truffleHog`/`detect-secrets`/`git-secrets` e `pip-audit`/`bandit`.

## 7) Checklist mínimo antes de executar

- [ ] Fazer clone mirror e verificar integridade
- [ ] Comunicar time + janela de manutenção
- [ ] Identificar todos os caminhos sensíveis (`backups/`, `*.sqlite3`, `*.dump`, `snapshots/`)
- [ ] Executar BFG/git-filter-repo em clone mirror e validar histórico localmente
- [ ] Rodar `git gc` e `git push --force`
- [ ] Rotacionar segredos e atualizar CI
- [ ] Forçar re-clone dos desenvolvedores

---

Se quiser, eu posso:
- gerar o script PowerShell/Batch para executar os passos com BFG (você rodará localmente), ou
- aplicar uma entrada em `.gitignore` e criar um PR com a documentação acima.

Escolha `script` ou `pr` e eu continuo.
