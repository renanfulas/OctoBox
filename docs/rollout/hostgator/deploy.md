<!--
FONTE DA VERDADE: workflow deploy-vps.yml seleciona o SHA e chama
scripts/linux/deploy_octobox.sh, única implementação de instalação.
Este runbook descreve o contrato local; não implica deploy executado.
-->

# Deploy — HostGator VPS

## Contrato de release

Cada release fica em `/srv/octobox/releases/<sha-completo>`, com worktree Git
detached, venv própria e `.release.env` imutável. `/srv/octobox/current` é o
ponteiro atômico usado pelo Gunicorn e pelos serviços Django. Segredos continuam
em `/srv/octobox/shared/octobox.env`; estáticos com hash são acumulados em
`/srv/octobox/shared/staticfiles` para manter referências de páginas já abertas.
O `.release-manifest` e `shared/deploy-state/deploy_run_id` registram SHA e ID
da execução do GitHub Actions (ou `manual` para contingência local).
O WhiteNoise usa `releases/<sha>/staticfiles` e o manifesto de assets daquela
release; Nginx usa o diretório shared acumulativo para servir também hashes de
releases anteriores.

O deploy aceita exclusivamente `--sha <40 caracteres lowercase>`, verifica que
esse objeto existe e continua sendo a HEAD de `origin/main`, instala dependências
na venv isolada, valida Django, coleta estáticos, faz backup PostgreSQL, executa
bootstrap/migrations e só então troca `current`. Migrações devem seguir
expand/contract para que a release anterior permaneça compatível. A troca reinicia
Gunicorn e valida que `deployed_sha` e `loaded_sha` correspondem ao SHA solicitado.

Repetir o SHA já ativo, ainda aprovado em `origin/main`, é um no-op somente se a
release tiver os artefatos necessários, manifesto/SHA/hash dos assets compatíveis
e health saudável com o mesmo SHA carregado. Nesse caso não há reinstalação,
migration, reativação nem alteração do ID da ativação ou do predecessor de rollback.
Um destino existente inativo, incompleto, divergente ou não saudável é recusado
antes da preparação. Uma preparação interrompida requer investigação e recuperação
operacional explícitas; o script não remove nem repara o diretório automaticamente.
Reativar release anterior segue o procedimento separado de rollback.

Esta política tem testes locais de helpers Bash; seu aceite de permissões,
serviços e ciclo A→B→A ainda depende de ensaio no host Linux descartável.

## Caminho de execução

O deploy é iniciado exclusivamente pelo workflow `VPS Deploy (Hostgator São
Paulo)`, na `main`, com SHA completo e gates aprovados para o mesmo SHA. Não há
deploy manual por SSH: o antigo launcher Windows foi desativado porque enviava
o script do checkout local e não verificava os gates. O lock no host continua
impedindo deploy e rollback concorrentes.

Em emergência, rollback é uma ação separada e segue o procedimento autorizado em
[rollback.md](rollback.md); ele não publica código novo nem reverte migrations.

## Instalação/migração inicial do layout

Antes do primeiro uso, o provisionamento precisa manter `/srv/octobox/app` como
checkout Git de bootstrap (somente fetch/worktree), criar `/srv/octobox/shared`,
instalar os unit files atualizados e alterar o alias `/static/` no Nginx para
`/srv/octobox/shared/staticfiles/`. Validar permissões, executar
`systemctl daemon-reload`, `nginx -t` e reload do Nginx em janela operacional.
Esse bootstrap ainda não foi executado na VPS.

## Evidência pós-deploy

1. `systemctl is-active octobox-gunicorn` retorna `active`.
2. `/api/v1/health/` responde `healthy=true`, `release_consistent=true`, e
   `deployed_sha == loaded_sha == SHA aprovado`.
3. Executar [smoke.md](smoke.md), incluindo os corredores autenticados e por
   tenant aplicáveis.
4. Em falha depois da ativação, o script tenta restaurar o ponteiro anterior e
   validar novamente. Também repõe o predecessor de rollback registrado antes
   da tentativa (ou sua ausência), para que voltar à release ativa não perca
   a opção de rollback que já existia. Se isso não resolver, siga [rollback.md](rollback.md).

O script não desfaz migrações automaticamente. Restore de banco é um procedimento
separado, orientado por evidência e pelo backup registrado em
`shared/deploy-state/last_backup_path`.

O worker longo `octobox-public-workout-rest-alerts`, quando instalado, também
reinicia após restauração do ponteiro. Na falha da primeira ativação, sem release
anterior, ele é parado. Falha no restart emite aviso e não suprime o health principal
nem sua tentativa de recuperação. Conferir o worker separadamente no host: health
HTTP aprovado não comprova sua disponibilidade. Esses caminhos têm testes locais
com systemctl simulado; o ensaio operacional permanece pendente.
