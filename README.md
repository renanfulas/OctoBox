<!--
ARQUIVO: visao publica principal do projeto.

POR QUE ELE EXISTE:
- Explica o produto, sua arquitetura, fluxo de execucao e orientacao inicial para quem entra no repositorio.

O QUE ESTE ARQUIVO FAZ:
1. Resume o escopo funcional atual.
2. Explica a estrutura do projeto.
3. Documenta execucao local e caminhos de deploy/homologacao.

TIPO DE DOCUMENTO:
- porta de entrada institucional e estrategica

AUTORIDADE:
- alta para contexto geral do repositorio

DOCUMENTO PAI:
- nenhum; este e o ponto de entrada publico do repositorio

QUANDO USAR:
- quando a duvida for o que e o produto, qual a direcao principal e qual documento abrir primeiro

PONTOS CRITICOS:
- Este arquivo precisa acompanhar a realidade do produto para nao vender uma versao falsa do sistema.
- Este arquivo nao deve virar guia detalhado de depuracao ou mapa exaustivo de codigo.
-->

# OctoBox Control

OctoBox e uma central operacional para boxes e academias que precisam sair do improviso de WhatsApp, planilhas e admin bruto demais para a rotina real.

## Preview Visual

Abaixo, os vislumbres da interface moderna do OctoBox.

<p align="center">
  <img src="docs/screenshots/dashboard-dark.png" width="48%" alt="Dashboard Dark" />
  <img src="docs/screenshots/dashboard-light.png" width="48%" alt="Dashboard Light" />
</p>

<p align="center">
  <img src="docs/screenshots/class-grid-dark.png" width="48%" alt="Grade de Aulas" />
  <img src="docs/screenshots/students-list-dark.png" width="48%" alt="Gestão de Alunos" />
</p>

## Problema que o OctoBox resolve

Na pratica, muitos boxes crescem com operacao fragmentada: lead no WhatsApp, aluno em planilha, cobranca em controle manual, agenda em memoria da equipe e decisao gerencial sem leitura confiavel. O resultado costuma ser retrabalho, perda de oportunidade comercial, atraso financeiro, falha de acompanhamento e rotina dependente demais de quem esta atendendo.

## Solucao proposta pelo projeto

O OctoBox foi desenhado para concentrar essa operacao em um fluxo unico, claro e utilizavel no dia a dia. Ele conecta alunos, intake, planos, matriculas, cobrancas, grade de aulas, presenca, auditoria e leitura gerencial em uma base operacional simples de navegar. A proposta do projeto e transformar rotina dispersa em processo visivel, rastreavel e acionavel para recepcao, gerencia, coach e owner.

## Marco de execucao

O primeiro marco funcional do projeto foi entregue em menos de 24 horas.

Linha do tempo deste primeiro ciclo:

1. inicio do projeto em 10/03/2026
2. marco funcional principal atingido em 11/03/2026
3. primeira versao pronta para operacao, com base funcional validada e evolucao futura concentrada em novas features, refinamentos e melhorias

## Escopo atual

- base de alunos com telefone principal legado, mas com identidade de canal de WhatsApp ja endurecida por blind index pesquisavel
- central de intake para leads e entradas provisiorias antes do cadastro definitivo, com payload estruturado para rastreio futuro
- fluxo leve de cadastro e edicao de aluno com conversao de intake
- conexao imediata entre aluno, plano, matricula e cobranca inicial
- cobranca unica, parcelada ou recorrente a partir da ficha do aluno
- acoes diretas na ficha do aluno para atualizar cobranca, marcar pagamento, cancelar, estornar, regenerar e reativar matricula
- centro visual de financeiro com filtros por janela, plano, status e metodo
- navegacao de shell e atalhos operacionais consolidados por contrato central de rotas
- dashboard inicial para leitura rapida da operacao
- aulas, presenca, check-in, check-out, faltas e ocorrencias operacionais
- autenticacao propria com papeis owner, dev, manager, recepcao e coach
- navegacao filtrada por papel
- trilha de auditoria para login, logout, mudancas no admin e acoes sensiveis do produto

## Estado operacional atual

- pilha recente de endurecimento ja aterrissada na `main`
- contrato de identidade WhatsApp com blind index, backfill historico e constraint de unicidade
- contrato de navegacao do shell estabilizado nas superficies centrais
- fluxo visual de alunos e financeiro atualizado e protegido por testes de catalogo e financeiro
- workflow de CI para performance e integridade ja acompanha migrate, fixture loading e baseline de Postgres suportada
- admin endurecido por caminho privado configuravel e gate centralizado por papel
- throttle por escopo ativo para login, admin, writes, exports, dashboard, leituras pesadas e autocomplete
- cache compartilhada opcional via Redis, com fallback local e degradacao segura quando o cache externo falhar
- presenters e page payloads consolidados nas superficies centrais de dashboard, catalogo, guide e operations

## Como usar a documentacao

Use os docs por nivel de pergunta:

1. este README explica o produto, o estado atual e a direcao geral
2. o [docs/reference/documentation-authority-map.md](docs/reference/documentation-authority-map.md) diz qual doc vence quando houver conflito, idade ou ambiguidade
3. os docs em [docs/architecture](docs/architecture) definem tese, principios e rumo estrutural
4. os docs em [docs/plans](docs/plans) definem frentes ativas e ordem de execucao
5. o [docs/reference/reading-guide.md](docs/reference/reading-guide.md) serve para navegar no codigo e depurar a base, nao para definir direcao de produto
6. os docs em [docs/rollout](docs/rollout) servem para publicacao, homologacao e operacao de campo

## Governanca OctoBox

O projeto usa tres trilhos de governanca para nao virar uma obra onde cada pessoa olha um mapa diferente:

1. documentacao e precedencia: [docs/reference/documentation-authority-map.md](docs/reference/documentation-authority-map.md)
2. convencoes tecnicas e C.O.R.D.A.: [.specs/codebase/CONVENTIONS.md](.specs/codebase/CONVENTIONS.md)
3. leitura tecnica do runtime: [docs/reference/reading-guide.md](docs/reference/reading-guide.md)

Traducao pratica:

1. `C.O.R.D.A.` significa `Contexto`, `Objetivo`, `Riscos`, `Direcao` e `Acoes`
2. use esse framework quando estivermos fechando beta, priorizando UX ou decidindo entre polimento e correcao estrutural
3. primeiro alinhamos o terreno, depois escolhemos a rota; isso evita passar verniz numa porta que ainda nao fecha direito

## Leitura rapida do produto

Hoje o sistema tem tres camadas principais:

1. operacao por papel
2. catalogo visual para alunos e financeiro
3. backoffice admin e auditoria

Importante para leitura tecnica atual:

1. `boxcore` ja nao deve ser lido como centro do runtime
2. ele permanece no projeto como app legado de estado do Django
3. o runtime atual deve preferir apps reais como `access`, `catalog`, `operations`, `students`, `finance`, `auditing`, `communications`, `api`, `integrations` e `jobs`

Nas areas com maior volume de regra, a base foi organizada de forma mais explicita:

1. views HTTP por dominio
2. queries e snapshots de leitura
3. actions e workflows de regra de negocio

Este README para na camada institucional e estrategica. Para navegar arquivo por arquivo, sequencia de leitura, pontos de bug e fronteiras tecnicas do runtime, use o [docs/reference/reading-guide.md](docs/reference/reading-guide.md).

Se quiser estudar a base em ordem pedagógica, use [docs/reference/reading-guide.md](docs/reference/reading-guide.md).

Se quiser entender como o CSS do projeto deve ser organizado, expandido e debugado sem virar remendo acumulado, use [docs/experience/css-guide.md](docs/experience/css-guide.md).

Se quiser entender especificamente o que ainda prende o estado historico em `boxcore`, use [docs/architecture/boxcore-model-state-plan.md](docs/architecture/boxcore-model-state-plan.md) e [docs/architecture/boxcore-state-residue-inventory.md](docs/architecture/boxcore-state-residue-inventory.md).

Se quiser entender a direcao tecnica para crescer sem perder simplicidade, use [docs/architecture/architecture-growth-plan.md](docs/architecture/architecture-growth-plan.md).

Se quiser entender a estrategia especifica para fazer o negocio deixar de depender de Django como core, use [docs/architecture/django-core-strategy.md](docs/architecture/django-core-strategy.md) e [docs/architecture/django-decoupling-blueprint.md](docs/architecture/django-decoupling-blueprint.md).

Se quiser entender a declaracao oficial de qual passa a ser o centro conceitual do sistema, use [docs/architecture/octobox-conceptual-core.md](docs/architecture/octobox-conceptual-core.md).

Se quiser entender o novo CENTER arquitetural que separa nivel de acesso e nucleo interno, use [docs/architecture/center-layer.md](docs/architecture/center-layer.md).

Se quiser entender a estrutura complementar de sinais, integracoes e expansao transversal do sistema, use [docs/architecture/signal-mesh.md](docs/architecture/signal-mesh.md).

Se quiser entender como a arquitetura trata suportes temporarios de construcao sem confundi-los com a estrutura final, use [docs/architecture/scaffold-agents.md](docs/architecture/scaffold-agents.md).

Se quiser entender a grande fachada frontal do produto, onde a experiencia visivel precisa continuar limpa mesmo com obra lateral e transicao arquitetural, use [docs/experience/front-display-wall.md](docs/experience/front-display-wall.md).

Se quiser o plano oficial para reorganizar o front-end de forma alinhada com a Front Display Wall, com contratos claros de tela e encaixe futuro no movimento de desacoplamento do Django, use [docs/plans/front-end-restructuring-guide.md](docs/plans/front-end-restructuring-guide.md).

Se quiser o blueprint especifico do catalogo para padronizar `page payload` e `presenter` em alunos, ficha, financeiro, plano e grade, use [docs/plans/catalog-page-payload-presenter-blueprint.md](docs/plans/catalog-page-payload-presenter-blueprint.md).

Se quiser o passo a passo oficial para pensar, montar e validar layouts do site mantendo prioridade, pendencia e proxima acao como criterio estrutural, use [docs/experience/layout-decision-guide.md](docs/experience/layout-decision-guide.md).

Se quiser entender o plano do novo modulo de Recepcao, sua fronteira funcional, custo atual versus custo futuro e por que essa area foi reinterpretada como triunfo visivel da obra, use [docs/plans/reception-module-plan.md](docs/plans/reception-module-plan.md).

Se quiser entender a direcao oficial do segundo andar do produto para o aplicativo do celular, sua regra de limpeza visual, sua navegacao essencial e a tese de como o Octobox deve se tornar favorito na mao das pessoas, use [docs/experience/octobox-mobile-guide.md](docs/experience/octobox-mobile-guide.md).

Se quiser a traducao dessa direcao em telas concretas, ordem de prototipacao e hierarquia de navegacao do app mobile, use [docs/plans/octobox-mobile-screen-blueprint.md](docs/plans/octobox-mobile-screen-blueprint.md).

Se quiser entender a camada superior de emissao visivel e sinalizacao confiavel do estado do sistema, use [docs/architecture/red-beacon.md](docs/architecture/red-beacon.md).

Se quiser entender a escalada maxima de alerta e a mudanca de postura defensiva do predio, use [docs/architecture/vertical-sky-beam.md](docs/architecture/vertical-sky-beam.md) e [docs/architecture/alert-siren.md](docs/architecture/alert-siren.md).

Se quiser a baseline operacional de seguranca para deploy, throttles, proxies confiaveis e criterio inicial de blocklist sem chute, use [docs/reference/production-security-baseline.md](docs/reference/production-security-baseline.md) e [docs/reference/external-security-edge-playbook.md](docs/reference/external-security-edge-playbook.md).

Se quiser a traducao direta disso para regras do Cloudflare e postura fechada do admin, use [docs/reference/cloudflare-edge-rules.md](docs/reference/cloudflare-edge-rules.md).

Se quiser uma visao consolidada de todo o predio arquitetural em um unico documento, use [docs/architecture/octobox-architecture-model.md](docs/architecture/octobox-architecture-model.md).

Essa estrutura tambem passou a ser definida como elástica com baseline fixo, expansao controlada e retorno seguro ao estado basal quando houver risco estrutural.

Se quiser estudar o criterio arquitetural por tras das decisoes, reaplicar esse metodo em outros projetos e aprender os termos em linguagem simples, use [docs/reference/personal-architecture-framework.md](docs/reference/personal-architecture-framework.md), [docs/reference/architecture-terms-glossary.md](docs/reference/architecture-terms-glossary.md) e [docs/reference/personal-growth-roadmap.md](docs/reference/personal-growth-roadmap.md).

Se quiser entender o raciocinio da primeira entrega, as decisoes tomadas e o que eu aprendi no processo, veja [docs/history/v1-retrospective.md](docs/history/v1-retrospective.md).

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
|   |-- forms.py                 -> formularios leves de alunos, financeiro e grade de aulas
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
|       |-- class_schedule_workflows.py      -> criacao recorrente e limites da grade
|       |-- class_grid_commands.py           -> comandos operacionais da grade de aulas
|       |-- class_grid_dispatcher.py         -> despacho de form_kind e acoes da grade
|       |-- class_grid_policy.py             -> regras de edicao e exclusao da grade
|       |-- class_grid_messages.py           -> mensagens operacionais centralizadas da grade
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
|-- catalog/                     -> alunos, aluno-form, financeiro, grade de aulas e edicao de plano
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

## Fronteiras tecnicas ja abertas para crescimento

- /api/ -> entrada oficial da API do produto
- /api/v1/ -> manifesto da primeira versao da API
- /api/v1/health/ -> saude basica da fronteira externa
- identidade de canal ja prefere contato explicito de WhatsApp e id externo do provedor antes do fallback legado por telefone
- payloads de intake e logs de mensagem passam a ser gravados como JSON saneado, com limite e mascara de chaves sensiveis

## O que a grade de aulas entrega hoje

A tela [templates/catalog/class-grid.html](templates/catalog/class-grid.html) ja funciona como uma central operacional de agenda fora do admin.

Hoje ela entrega:

1. agenda de hoje com leitura de coach, horario, status e ocupacao
2. calendario das proximas duas semanas com acesso rapido a edicao
3. visao mensal compacta e calendario expandido
4. planejador recorrente com sequencia de horarios e bloqueio por limites diario, semanal e mensal
5. edicao rapida de aula com protecao para reabertura indevida e exclusao com historico
6. indicadores visuais de lotacao e estado em tempo real durante a execucao da aula

## Convencao de comentarios e cabecalhos

## Licenca

Este projeto esta licenciado sob a GNU Affero General Public License v3.0 (AGPL-3.0). Veja [LICENSE](LICENSE).

Todo arquivo relevante deve explicar rapidamente seu papel no topo.

Arquivos Markdown usam comentario HTML. Arquivos Python usam docstring no mesmo formato. A referencia completa e [docs/reference/new-file-template.md](docs/reference/new-file-template.md).

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
- recepcao: balcao, agenda, intake e cobranca curta no fluxo operacional
- coach: rotina tecnica de aulas, presenca e acompanhamento

O comando para preparar os grupos base e:

```bash
python manage.py bootstrap_roles
```

## Como rodar

1. Crie e ative o ambiente virtual.
2. Instale dependencias com `pip install -r requirements.txt`.
3. Copie `.env.example` para `.env` e ajuste o minimo necessario.
4. Rode `python manage.py migrate`.
5. Rode `python manage.py bootstrap_roles`.
6. Crie um usuario administrativo com `python manage.py createsuperuser`.
7. Suba o servidor com `python manage.py runserver`.
8. Rode `python manage.py test` para usar automaticamente a trilha de configuracao de testes do projeto.

Observacao:

- login, logout, mudancas no admin e acoes comerciais sensiveis ja alimentam a trilha de auditoria
- para ambiente local, o projeto le automaticamente `.env` quando ele existir
- `python manage.py test` prefere `config.settings.test` e tambem aceita `.env.test` local como complemento opcional
- para ambiente local, voce pode definir `DJANGO_SECRET_KEY` em um arquivo `.env` ou nas variaveis do sistema
- para ambientes que usam identidade de canal WhatsApp, defina tambem `PHONE_BLIND_INDEX_KEY`
- o projeto agora aceita `DJANGO_ENV=development` ou `DJANGO_ENV=production` para separar configuracao local de homologacao/producao
- para homologacao/producao, o caminho recomendado e usar `DATABASE_URL` com PostgreSQL, `REDIS_URL` para cache compartilhada, rodar `collectstatic` e publicar atras de HTTPS
- o caminho publico do admin deve ser definido por `DJANGO_ADMIN_URL_PATH`, nao por `/admin/`
- para abrir o servidor na rede local, use a task `Run Django Server (LAN)` ou rode `python manage.py runserver 0.0.0.0:8000`
- para CI ou homologacao com PostgreSQL, use Postgres 14 ou superior

Guias novos:

- deploy de homologacao: [docs/rollout/deploy-homologation.md](docs/rollout/deploy-homologation.md)
- backup minimo do banco: [docs/rollout/backup-guide.md](docs/rollout/backup-guide.md)
- baseline de seguranca de producao: [docs/reference/production-security-baseline.md](docs/reference/production-security-baseline.md)
- checklist de validacao mobile real: [docs/experience/mobile-real-validation-checklist.md](docs/experience/mobile-real-validation-checklist.md)
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
