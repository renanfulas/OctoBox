<!--
ARQUIVO: visao publica principal do projeto.

POR QUE ELE EXISTE:
- Explica o produto, sua arquitetura, fluxo de execucao e orientacao inicial para quem entra no repositorio.

O QUE ESTE ARQUIVO FAZ:
1. Resume o escopo funcional atual.
2. Explica a estrutura do projeto.
3. Documenta execucao local e caminhos de deploy/homologacao.

PONTOS CRITICOS:
- Este arquivo precisa acompanhar a realidade do produto para nao vender uma versao falsa do sistema.
-->

# OctoBox Control

Aplicacao Django para gestao de um box com foco em operacao real: alunos, intake, planos, matriculas, cobrancas, aulas, presenca, ocorrencias, auditoria e leitura gerencial.

## Escopo atual

- base de alunos com WhatsApp como identificador operacional principal
- central de intake para leads e entradas provisiorias antes do cadastro definitivo
- fluxo leve de cadastro e edicao de aluno com conversao de intake
- conexao imediata entre aluno, plano, matricula e cobranca inicial
- cobranca unica, parcelada ou recorrente a partir da ficha do aluno
- acoes diretas na ficha do aluno para atualizar cobranca, marcar pagamento, cancelar, estornar, regenerar e reativar matricula
- centro visual de financeiro com filtros por janela, plano, status e metodo
- dashboard inicial para leitura rapida da operacao
- aulas, presenca, check-in, check-out, faltas e ocorrencias operacionais
- autenticacao propria com papeis owner, dev, manager e coach
- navegacao filtrada por papel
- trilha de auditoria para login, logout, mudancas no admin e acoes sensiveis do produto

## Leitura rapida do produto

Hoje o sistema tem tres camadas principais:

1. operacao por papel
2. catalogo visual para alunos e financeiro
3. backoffice admin e auditoria

Nas areas com maior volume de regra, a base foi organizada de forma mais explicita:

1. views HTTP por dominio
2. queries e snapshots de leitura
3. actions e workflows de regra de negocio

Se quiser estudar a base em ordem pedagógica, use [docs/reading-guide.md](docs/reading-guide.md).

## Mapa do projeto

```text
boxcore/
|-- access/
|   |-- context_processors.py    -> monta sidebar e contexto global por papel
|   |-- roles/                   -> regras e capacidades de owner, dev, manager e coach
|   |-- urls.py                  -> login, logout, acessos e entrada do sistema
|   `-- views.py                 -> paginas de acesso e visao de papeis
|-- auditing/
|   |-- __init__.py              -> ponto de entrada da auditoria
|   `-- services.py              -> grava eventos sensiveis de forma padronizada
|-- admin/
|   |-- audit.py                 -> admin da trilha de auditoria
|   |-- finance.py               -> admin de planos, matriculas e pagamentos
|   |-- onboarding.py            -> admin da central de intake
|   |-- operations.py            -> admin operacional
|   |-- students.py              -> admin de alunos
|   `-- __init__.py              -> registra tudo no Django admin
|-- catalog/
|   |-- forms.py                 -> formularios leves de alunos e financeiro
|   |-- student_queries.py       -> snapshots e leituras da area de alunos
|   |-- finance_queries.py       -> snapshots e leituras da area financeira
|   |-- class_grid_queries.py    -> leituras da grade de aulas
|   |-- urls.py                  -> rotas das telas visuais de catalogo
|   |-- views/
|   |   |-- catalog_base_views.py -> base HTTP compartilhada do catalogo
|   |   |-- student_views.py      -> diretorio, cadastro leve e ficha do aluno
|   |   |-- finance_views.py      -> financeiro visual, planos e comunicacoes
|   |   `-- class_grid_views.py   -> grade visual de aulas
|   `-- services/
|       |-- student_workflows.py             -> fluxo leve de criacao e edicao de aluno
|       |-- student_enrollment_actions.py    -> acoes de matricula na ficha do aluno
|       |-- student_payment_actions.py       -> acoes de cobranca na ficha do aluno
|       |-- finance_communication_actions.py -> comunicacao financeira e follow-up
|       |-- membership_plan_workflows.py     -> criacao e edicao de planos
|       `-- operational_queue.py             -> fila operacional e metricas de retencao
|-- dashboard/
|   |-- dashboard_snapshot_queries.py -> snapshot consolidado do painel principal
|   |-- dashboard_views.py            -> camada HTTP do painel
|   |-- urls.py                  -> rotas do painel
|   `-- __init__.py              -> marcador do pacote de dashboard
|-- guide/
|   |-- urls.py                  -> rota do mapa interno do sistema
|   `-- views.py                 -> contexto pedagogico do mapa visual
|-- management/commands/
|   |-- bootstrap_roles.py       -> cria grupos de acesso
|   `-- import_students_csv.py   -> importa alunos por CSV usando WhatsApp como chave
|-- models/
|   |-- audit.py                 -> eventos de auditoria e rastreabilidade
|   |-- base.py                  -> classes base compartilhadas
|   |-- communications.py        -> base de contatos e logs de WhatsApp
|   |-- finance.py               -> planos, matriculas e pagamentos
|   |-- onboarding.py            -> intake e entrada provisoria
|   |-- operations.py            -> aulas, presenca e ocorrencias
|   |-- students.py              -> alunos e dados cadastrais
|   `-- __init__.py              -> exporta os modelos do app
|-- operations/
|   |-- workspace_snapshot_queries.py -> snapshots das areas operacionais por papel
|   |-- base_views.py                -> base HTTP compartilhada de operations
|   |-- workspace_views.py           -> workspaces de owner, dev, manager e coach
|   |-- action_views.py              -> endpoints mutaveis da operacao
|   |-- actions.py                   -> handlers das acoes operacionais
|   |-- urls.py                  -> rotas das areas operacionais por papel
|   `-- __init__.py              -> marcador do pacote operacional
`-- tests/
	|-- test_access.py           -> login e papeis
	|-- test_catalog.py          -> alunos, cobrancas, matriculas e grade visual
	|-- test_catalog_services.py -> services e workflows do catalogo
	|-- test_dashboard.py        -> painel principal
	|-- test_finance.py          -> centro financeiro visual
	|-- test_guide.py            -> mapa do sistema
	|-- test_import_students.py  -> importacao por CSV
	|-- test_operations_services.py -> handlers e services de operations
	`-- test_operations.py       -> operacao por papel

templates/
|-- access/                      -> login e visao de acessos
|-- catalog/                     -> alunos, aluno-form, financeiro e edicao de plano
|-- dashboard/                   -> painel principal
|-- guide/                       -> mapa visual do sistema
|-- layouts/                     -> layout base e navegacao global
`-- operations/                  -> telas operacionais por papel
```

## Rotas visuais mais importantes

- /dashboard/ -> resumo da operacao
- /alunos/ -> base principal, funil e busca comercial
- /alunos/novo/ -> cadastro leve de aluno com plano e cobranca
- /alunos/<id>/editar/ -> ficha comercial do aluno
- /financeiro/ -> leitura gerencial de planos, receita, churn e fila financeira
- /grade-aulas/ -> grade visual de aulas

## Convencao de comentarios e cabecalhos

Todo arquivo relevante deve explicar rapidamente seu papel no topo.

Arquivos Markdown usam comentario HTML. Arquivos Python usam docstring no mesmo formato.

Padrao para arquivos Python:

```python
"""
ARQUIVO: nome e funcao geral do arquivo.

POR QUE ELE EXISTE:
- motivo da existencia do arquivo no projeto.

O QUE ESTE ARQUIVO FAZ:
1. bloco principal 1
2. bloco principal 2
3. bloco principal 3

PONTOS CRITICOS:
- o que e perigoso mexer
- o que pode quebrar se for alterado sem cuidado
"""
```

Padrao para templates HTML:

```html
<!--
ARQUIVO: nome e funcao geral do template.

POR QUE ELE EXISTE:
- motivo da existencia do template.

O QUE ESTE ARQUIVO FAZ:
1. bloco principal 1
2. bloco principal 2
3. bloco principal 3
 
PONTOS CRITICOS:
- o que e perigoso mexer
- o que pode quebrar se for alterado sem cuidado
-->
```

Padrao para arquivos Markdown:

```html
<!--
ARQUIVO: nome e funcao geral do arquivo.

POR QUE ELE EXISTE:
- motivo da existencia do documento.

O QUE ESTE ARQUIVO FAZ:
1. contextualiza a area do sistema.
2. orienta leitura, manutencao ou operacao.
3. registra riscos e cuidados para quem editar.

PONTOS CRITICOS:
- manter aderencia com a estrutura real do projeto.
- revisar sempre que arquivos ou fluxos forem renomeados.
-->
```

## Papeis atuais do sistema

- owner: visao estrategica do box e acesso maximo de negocio
- dev: manutencao tecnica, inspecao, suporte e auditoria controlada
- manager: operacao administrativa, comercial, financeiro e alunos
- coach: rotina tecnica de aulas, presenca e acompanhamento

O comando para preparar os grupos base e:

```bash
python manage.py bootstrap_roles
```

## Como rodar

1. Crie e ative o ambiente virtual.
2. Instale dependencias com `pip install -r requirements.txt`.
3. Rode `python manage.py migrate`.
4. Rode `python manage.py bootstrap_roles`.
5. Crie um usuario administrativo com `python manage.py createsuperuser`.
6. Suba o servidor com `python manage.py runserver`.

Observacao:

- login, logout, mudancas no admin e acoes comerciais sensiveis ja alimentam a trilha de auditoria
- para ambiente local, voce pode definir `DJANGO_SECRET_KEY` em um arquivo `.env` ou nas variaveis do sistema
- o projeto agora aceita `DJANGO_ENV=development` ou `DJANGO_ENV=production` para separar configuracao local de homologacao/producao
- para homologacao/producao, o caminho recomendado e usar `DATABASE_URL` com PostgreSQL, rodar `collectstatic` e publicar atras de HTTPS

Guias novos:

- deploy de homologacao: [docs/deploy-homologation.md](docs/deploy-homologation.md)
- backup minimo do banco: [docs/backup-guide.md](docs/backup-guide.md)
- scripts de backup: [scripts/backup_sqlite.ps1](scripts/backup_sqlite.ps1) e [scripts/backup_postgres.ps1](scripts/backup_postgres.ps1)

## Importacao inicial de alunos

O projeto inclui um comando para importar alunos por CSV usando WhatsApp como chave de deduplicacao.

Colunas suportadas:

- full_name
- whatsapp ou phone
- email
- gender
- birth_date no formato AAAA-MM-DD
- health_issue_status
- cpf
- status
- notes

Execucao:

```bash
python manage.py import_students_csv caminho/para/alunos.csv
```

## Ideias que podem ser inteligentes

- adicionar exportacao de relatorios financeiros e comerciais
- aprofundar a camada de acompanhamento de recorrencia e renegociacao
- ampliar auditoria para revisao operacional por papel
- preparar integracoes futuras com WhatsApp, avaliacao fisica e cobranca externa
