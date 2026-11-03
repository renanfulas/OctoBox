<!--
ARQUIVO: memória operacional de revisão e publicação de treinos no Curva.

TIPO DE DOCUMENTO:
- retrospectiva curta e melhoria contínua do fluxo de publicação.

AUTORIDADE:
- histórica; o runtime e o runbook atual prevalecem se houver divergência.

DOCUMENTO RELACIONADO:
- [guia-montagem-treino-curva.md](guia-montagem-treino-curva.md)
- [public-workouts-operacao.md](../runbooks/public-workouts-operacao.md)

O QUE ESTE ARQUIVO FAZ:
1. registra a fricção observada numa publicação real via SSH.
2. descreve o comando criado para revisar e publicar com guardas explícitas.
3. registra os limites que ainda precisam de evolução.

PONTOS CRITICOS:
- publicação de código em produção só pelo workflow aprovado na main.
- publicação de treino continua passando pela aprovação humana e pelo serviço oficial.
-->

# Memória operacional: publicação Curva — 2026-11-03

## O que aconteceu

Uma revisão de programa existente foi feita por SSH autorizado. O processo
consultou a versão ativa e o rascunho, editou o payload, validou o schema,
revisou o treino e o diff, recebeu aprovação explícita no chat e chamou
`approve_and_publish_draft`. A publicação criou uma nova versão imutável e
ativa; a versão anterior ficou inativa.

A publicação passou pelo serviço transacional existente, mas a operação remota
usou vários blocos Python inline no `manage.py shell`. As consultas exigiram
descobrir os nomes reais dos campos e as conferências de payload, base, versão
ativa, status do rascunho e outbox foram feitas separadamente. Como a aprovação
veio de fora do Django Admin, `reviewed_by` ficou vazio e a trilha perdeu a
identidade do revisor.

## Melhorias incorporadas

Foi criado `public_workouts/management/commands/review_public_workout_program_draft.py`.
Depois de implantado, ele:

1. funciona em modo somente leitura por padrão;
2. mostra status do rascunho, versão-base, versão ativa, validação e plano;
3. compara metadados, dias e movimentos contra a versão-base;
4. pode imprimir o JSON integral com `--show-json`;
5. verifica a versão ativa esperada e exige um usuário Django ativo com acesso
   de equipe antes de publicar;
6. chama `approve_and_publish_draft`, confirma a versão ativa e mostra o estado
   do item de onboarding e da outbox `program_ready`.

Uso:

```bash
python manage.py review_public_workout_program_draft --draft-id <id> --show-json
python manage.py review_public_workout_program_draft --draft-id <id> --publish \
  --expected-active-version <versao-revisada> --reviewed-by <username-da-equipe>
```

O admin continua preferível quando a pessoa revisora está autenticada. O
comando facilita a revisão remota e mantém a aprovação explícita e atribuída.
Ele não edita o payload; alterações continuam sendo feitas no rascunho pelo
admin ou por uma operação manual controlada.

## Aprendizados operacionais

- Uma mensagem `program_ready` em estado `pending` está aguardando o processador
  assíncrono; isso não desfaz a versão ativa e não prova que o aviso já chegou.
- `curva_publication_without_work_item` indica que a publicação não encontrou
  item de onboarding ativo para concluir. Isso pode ser esperado antes do
  preenchimento da anamnese; confira o runbook antes de reconciliar itens.
- A publicação do treino e a entrega do aviso são estados separados. Nunca
  republique o programa só para tentar enviar o e-mail novamente.
- O payload deve ser revisto inteiro e o diff deve ser conferido antes da
  aprovação; não usar `publish_program` diretamente para contornar a revisão.

## Limites e próximo passo

O comando e esta memória estão no workspace. A VPS não aceita deploy manual por
SSH: código deve chegar à `main` pelo workflow `VPS Deploy (Hostgator São Paulo)`
com SHA aprovado e gates concluídos. Até essa implantação, o comando não existe
na produção.

O comando reduz consultas e erros no caminho remoto, mas não oferece prévia
visual de rascunho nem edição estruturada fora do Admin. A próxima melhoria de
produto é uma prévia autenticada do payload pendente que não crie versão ativa,
outbox nem acesso para o aluno.

## Preflight de produção — 2026-11-03

O pedido de deploy foi autorizado, mas o preflight revelou que a VPS ainda usa
o layout legado: `/srv/octobox/current` e `/srv/octobox/releases` não existem,
e o unit do Gunicorn aponta para `/srv/octobox/venv` e `/srv/octobox/app`.
O endpoint de health respondeu saudável com `deployed_sha`, mas não expôs
`loaded_sha` nem `release_consistent`; o arquivo `deploy-state/current_commit`
registrou um SHA diferente do endpoint.

O workflow de release espera que o Gunicorn use `/srv/octobox/current`. O
`bootstrap_hostgator_octobox.sh` disponível na `main` instala o layout legado
e não faz essa migração. A rotina de deploy, sem uma release anterior, pode
parar o Gunicorn se a primeira ativação falhar. Por isso, o PR do comando foi
mantido em draft. Antes de mesclar ou disparar o workflow, o runbook exige
preparar `shared`, instalar os units atualizados, ajustar o alias `/static/`
do Nginx e validar o layout em janela operacional. Essa migração precisa ser
planejada e aprovada como alteração de infraestrutura separada.
