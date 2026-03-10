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
|   |-- urls.py                  -> rotas das telas visuais de catalogo
|   `-- views.py                 -> alunos, financeiro e grade em experiencia leve
|-- dashboard/
|   |-- urls.py                  -> rotas do painel
|   `-- views.py                 -> logica do dashboard
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
|   |-- urls.py                  -> rotas das areas operacionais por papel
|   `-- views.py                 -> telas e acoes exclusivas por papel
`-- tests/
	|-- test_access.py           -> login e papeis
	|-- test_catalog.py          -> alunos, cobrancas, matriculas e grade visual
	|-- test_dashboard.py        -> painel principal
	|-- test_finance.py          -> centro financeiro visual
	|-- test_guide.py            -> mapa do sistema
	|-- test_import_students.py  -> importacao por CSV
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
- dependencia de contexto ou logica critica.
-->
```

Regras praticas:

- comentarios internos devem ser raros e reservados para logica critica
- migrations podem ter cabecalho, mas nao devem ser reescritas sem necessidade
- se um arquivo crescer demais, divida por assunto antes de empilhar mais responsabilidade
- o template base para novos arquivos continua em [docs/new-file-template.md](docs/new-file-template.md)

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

## Proximos passos sugeridos

- mover partes mais densas da logica comercial de catalog/views.py para services dedicados
- adicionar exportacao de relatorios financeiros e comerciais
- aprofundar a camada de acompanhamento de recorrencia e renegociacao
- ampliar auditoria para revisao operacional por papel
- preparar integracoes futuras com WhatsApp, avaliacao fisica e cobranca externa