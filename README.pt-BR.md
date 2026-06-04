<!--
ARQUIVO: anexo oficial em portugues do README principal.

POR QUE ELE EXISTE:
- preserva a documentacao em portugues enquanto o README oficial do repositorio passa a ser em ingles.

O QUE ESTE ARQUIVO FAZ:
1. mantem a versao em portugues do README institucional.
2. oferece referencia local para leitura em pt-BR.
3. evita perda de contexto durante a transicao de idioma.

TIPO DE DOCUMENTO:
- anexo linguistico institucional

AUTORIDADE:
- complementar ao README principal em ingles

DOCUMENTO PAI:
- README.md

QUANDO USAR:
- quando a leitura em portugues for mais util para onboarding, alinhamento interno ou consulta rapida

PONTOS CRITICOS:
- este arquivo deve permanecer semanticamente alinhado ao README oficial em ingles.
- mudancas estruturais no README principal devem refletir aqui quando necessario.
-->

# README em Portugues do Brasil

Este arquivo e o anexo oficial em portugues do README principal. A versao oficial em ingles esta em [README.md](README.md).

# OctoBox Control

OctoBox e uma central operacional para boxes e academias que precisam sair do improviso de WhatsApp, planilhas e admin bruto demais para a rotina real.

## Preview Visual

Abaixo estao capturas recentes do runtime atual: a superficie de comando do owner, a fila financeira e a visao mobile-first de comando.

<p align="center">
  <img src="docs/screenshots/dashboard-current.png" width="48%" alt="Superficie de comando do owner" />
  <img src="docs/screenshots/finance-current.png" width="48%" alt="Superficie da fila financeira" />
</p>

<p align="center">
  <img src="docs/screenshots/dashboard-mobile-current.png" width="34%" alt="Superficie mobile de comando" />
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
- app do aluno com identidade propria, entrada por convite, troca de box ativo, shell PWA online-first, grade, WOD, RM, configuracoes e suporte offline
- fila financeira com analitica de follow-up, leitura de risco e outreach operacional semiassistido
- superficie de quick sales integrada ao financeiro do aluno
- pipeline de importacao de leads com roteamento por volume, policy operacional e trilho noturno de execucao

## Estado operacional atual

- runtime multi-tenant vivo em producao: `django-tenants` schema-per-tenant, o control plane `control` provisionando cada box em seu proprio schema Postgres, e o primeiro box provisionado em 23/05/2026 com um aluno real autenticando via OAuth
- isolamento de tenant sob teste antes da escala: boundary tests (B1-B12), namespace de cache por box e comandos de rollout (`provision_box`, `archive_box`, `smoke_test_tenant`) escritos antes da necessidade
- funil comercial de entrada em `signup` ja conectado a checkout Stripe, magic link e ativacao de tenant
- pilha recente de endurecimento ja aterrissada na `main`
- contrato de identidade WhatsApp com blind index, backfill historico e constraint de unicidade
- contrato de navegacao do shell estabilizado nas superficies centrais
- fluxo visual de alunos e financeiro atualizado e protegido por testes de catalogo e financeiro
- analitica de follow-up financeiro, leitura de fila de retencao e fundacao de churn ja vivem na superficie visual do financeiro
- diretorio de alunos agora carrega atalhos operacionais por KPI, leitura de crescimento em 30 dias e quick panel expandido
- superficies de owner, manager, recepcao e dev ja absorvem os contratos mais novos de shell compartilhado e page payload
- workflow de CI para performance e integridade ja acompanha migrate, fixture loading e baseline de Postgres suportada
- admin endurecido por caminho privado configuravel e gate centralizado por papel
- throttle por escopo ativo para login, admin, writes, exports, dashboard, leituras pesadas e autocomplete
- cache compartilhada opcional via Redis, com fallback local e degradacao segura quando o cache externo falhar
- presenters e page payloads consolidados nas superficies centrais de dashboard, catalogo, guide e operations
- fluxos de identidade e membership do app do aluno ja promovidos, incluindo convite e troca de box
- shell atual do app do aluno ja absorve a direcao de Grade, WOD e RM
- execucao de importacao de leads ja possui pipeline documentado, trilho em background e suporte a scheduler noturno
- probes de pagina publicada, request timing e telemetria de timing do snapshot financeiro ja informam a frente atual de performance
- a documentacao agora tambem possui uma camada guiada em `docs/guides/` para onboarding por tema e por perfil

## Fotografia atual do projeto

Hoje o projeto e melhor descrito como:

1. um monolito modular multi-tenant orientado por dominio, com isolamento schema-per-tenant via `django-tenants` e um control plane `control` separado do runtime do tenant
2. com `boxcore` preservado como estado historico do Django dentro do schema de cada tenant, e nao como a melhor explicacao do runtime atual
3. com fachadas publicas mais fortes, contratos de page payload e montagem de tela orientada por presenter
4. com uma superficie real de app do aluno e PWA ja em movimento ao lado da operacao web principal
5. ja habitado em producao: o primeiro box foi provisionado em 23/05/2026 e o primeiro aluno real autenticou via OAuth
6. com trabalho ativo concentrado em disciplina de performance, importacao operacional, experiencia do aluno e na transicao de escala do closed beta para multitenancy aberto

## Como usar a documentacao

Use os docs por nivel de pergunta:

1. este README explica o produto, o estado atual e a direcao geral
2. o [docs/reference/documentation-authority-map.md](docs/reference/documentation-authority-map.md) diz qual doc vence quando houver conflito, idade ou ambiguidade
3. o [docs/guides/README.md](docs/guides/README.md) entrega uma camada guiada de leitura para arquitetura, metodologia, backend, frontend, CSS, performance, seguranca e onboarding por perfil
4. os docs em [docs/architecture](docs/architecture) definem tese, principios e rumo estrutural
5. os docs em [docs/plans](docs/plans) definem frentes ativas e ordem de execucao
6. o [docs/reference/reading-guide.md](docs/reference/reading-guide.md) serve para navegar no codigo e depurar a base, nao para definir direcao de produto
7. o [docs/map/1-map-by-tests.md](docs/map/1-map-by-tests.md) mapeia o esqueleto vivo do projeto a partir da suite atual de testes
8. os docs em [docs/rollout](docs/rollout) servem para publicacao, homologacao e operacao de campo

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

Hoje o sistema tem quatro camadas principais de produto:

1. operacao por papel
2. catalogo visual para alunos e financeiro
3. app do aluno e superficie de identidade
4. backoffice admin e auditoria

Importante para leitura tecnica atual:

1. `boxcore` ja nao deve ser lido como centro do runtime
2. ele permanece no projeto como app legado de estado do Django, agora ancorando os models de dominio dentro do schema de cada tenant
3. o runtime atual deve preferir apps reais como `access`, `catalog`, `operations`, `students`, `finance`, `auditing`, `communications`, `api`, `integrations`, `jobs`, `guide`, `quick_sales`, `knowledge` e `student_app`
4. a camada de plataforma vive no schema public e existe antes de qualquer tenant: `control` (control plane), `signup` (funil comercial) e `student_identity` (identidade do aluno cross-box)

Nas areas com maior volume de regra, a base foi organizada de forma mais explicita:

1. views HTTP por dominio
2. queries e snapshots de leitura
3. actions e workflows de regra de negocio

Este README para na camada institucional e estrategica. Para navegar arquivo por arquivo, sequencia de leitura, pontos de bug e fronteiras tecnicas do runtime, use o [docs/reference/reading-guide.md](docs/reference/reading-guide.md).

Se quiser estudar a base em ordem pedagogica, use [docs/reference/reading-guide.md](docs/reference/reading-guide.md).

Se quiser entender como o CSS do projeto deve ser organizado, expandido e debugado sem virar remendo acumulado, use [docs/experience/css-guide.md](docs/experience/css-guide.md).

Se quiser entender especificamente o que ainda prende o estado historico em `boxcore`, use [docs/architecture/boxcore-model-state-plan.md](docs/architecture/boxcore-model-state-plan.md) e [docs/architecture/boxcore-state-residue-inventory.md](docs/architecture/boxcore-state-residue-inventory.md).

Se quiser entender a direcao tecnica para crescer sem perder simplicidade, use [docs/architecture/architecture-growth-plan.md](docs/architecture/architecture-growth-plan.md).

Se quiser entender onde inteligencia operacional, score, previsao e ML devem viver na arquitetura sem contaminar o core transacional, use [docs/architecture/operational-intelligence-ml-layer.md](docs/architecture/operational-intelligence-ml-layer.md).

Se quiser entender a estrategia especifica para fazer o negocio deixar de depender de Django como core, use [docs/architecture/django-core-strategy.md](docs/architecture/django-core-strategy.md) e [docs/architecture/django-decoupling-blueprint.md](docs/architecture/django-decoupling-blueprint.md).

Se quiser entender a declaracao oficial de qual passa a ser o centro conceitual do sistema, use [docs/architecture/octobox-conceptual-core.md](docs/architecture/octobox-conceptual-core.md).

Se quiser entender o novo CENTER arquitetural que separa nivel de acesso e nucleo interno, use [docs/architecture/center-layer.md](docs/architecture/center-layer.md).

Se quiser entender o runtime multi-tenant — schema-per-tenant com `django-tenants`, o control plane `control`, o Hybrid Identity Model e como um box e provisionado e isolado — use [docs/plans/schema-per-tenant-migration-plan.md](docs/plans/schema-per-tenant-migration-plan.md), o indice [docs/adr/README.md](docs/adr/README.md) (`ADR-005` a `ADR-010`) e [docs/architecture/center-layer.md](docs/architecture/center-layer.md). Para o rumo de abertura a mais boxes, use [docs/plans/scale-transition-20-100-open-multitenancy-plan.md](docs/plans/scale-transition-20-100-open-multitenancy-plan.md).

Se quiser entender a estrutura complementar de sinais, integracoes e expansao transversal do sistema, use [docs/architecture/signal-mesh.md](docs/architecture/signal-mesh.md).

Se aparecer duvida sobre a pasta espelho `OctoBox/`, trate-a como legado isolado e use [docs/reference/octobox-mirror-legacy-status.md](docs/reference/octobox-mirror-legacy-status.md).

Se aparecer duvida sobre `prompts/`, `prototypes/` ou materiais de apoio e arquivo, use [docs/reference/support-material-map.md](docs/reference/support-material-map.md).

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

Essa estrutura tambem passou a ser definida como elastica com baseline fixo, expansao controlada e retorno seguro ao estado basal quando houver risco estrutural.

Se quiser estudar o criterio arquitetural por tras das decisoes, reaplicar esse metodo em outros projetos e aprender os termos em linguagem simples, use [docs/reference/personal-architecture-framework.md](docs/reference/personal-architecture-framework.md), [docs/reference/architecture-terms-glossary.md](docs/reference/architecture-terms-glossary.md) e [docs/reference/personal-growth-roadmap.md](docs/reference/personal-growth-roadmap.md).

Se quiser entender o raciocinio da primeira entrega, as decisoes tomadas e o que eu aprendi no processo, veja [docs/history/v1-retrospective.md](docs/history/v1-retrospective.md).

## Fotografia arquitetural

Em nivel publico, o repositorio fica mais facil de entender em sete fatias:

1. `control`, `signup`, `student_identity`
   plataforma e tenancy no schema public: control plane (`Box`, `Domain`, `Membership`), funil Early Adopters e identidade do aluno cross-box
2. `access`, `dashboard`, `catalog`, `operations`, `guide`, `quick_sales`
   operacao web principal, workspaces por papel, alunos, financeiro, grade de aulas, superficie de guide interno e venda rapida
3. `student_app`
   shell PWA do aluno, convite, troca de box ativo, Grade, WOD, RM e suporte offline
4. `communications`, `integrations`, `api`, `jobs`, `knowledge`
   fronteiras externas, mensageria, webhooks, superficie de API, trabalho assincrono e o RAG interno do projeto
5. `shared_support`, `monitoring`, `reporting`, `model_support`
   contratos transversais, performance, helpers de runtime, observabilidade e estruturas base
6. `boxcore`
   estado historico do Django, ancora de migrations e superficie de compatibilidade dentro do schema de cada tenant
7. `docs`, `.specs`, `tests`, `scripts`
   governanca, planos, rollout, leitura tecnica, validacao e ferramental operacional

Se voce precisar da ordem de leitura em nivel de codigo, ownership e pontos de depuracao, pule para [docs/reference/reading-guide.md](docs/reference/reading-guide.md) em vez de usar este README como inventario arquivo por arquivo.

## Superficies centrais do produto

- /dashboard/ -> resumo da operacao
- /operacao/owner/ ou rotas operacionais por papel -> superficies de comando por papel
- /alunos/ -> base principal, funil e busca comercial
- /alunos/novo/ -> cadastro leve de aluno com plano e cobranca
- /alunos/<id>/editar/ -> ficha comercial do aluno
- /financeiro/ -> leitura gerencial de planos, receita, churn e fila financeira
- /grade-aulas/ -> grade visual de aulas
- /aluno/ -> home do app do aluno
- /aluno/grade/ -> agenda do app do aluno
- /aluno/wod/ e /aluno/rm/ -> treino e recordes pessoais do aluno

## Fronteiras externas e de crescimento

- /api/ -> entrada oficial da API do produto
- /api/v1/ -> manifesto da primeira versao da API
- /api/v1/health/ -> saude basica da fronteira externa
- identidade de canal ja prefere contato explicito de WhatsApp e id externo do provedor antes do fallback legado por telefone
- payloads de intake e logs de mensagem passam a ser gravados como JSON saneado, com limite e mascara de chaves sensiveis

## Convencoes de engenharia

Todo arquivo relevante deve explicar rapidamente seu papel no topo.

Para o padrao de cabecalho e o template oficial de arquivos, use [docs/reference/new-file-template.md](docs/reference/new-file-template.md).

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

O runtime e multi-tenant via `django-tenants` (schema-per-tenant), e o isolamento real de schema so funciona em PostgreSQL. Um schema local rapido (SQLite) basta para ler codigo e rodar parte da suite, mas o runtime fiel — e o CI — usa PostgreSQL, aplica migrations com `migrate_schemas` e provisiona cada box em seu proprio schema com `provision_box`. Para o setup multi-tenant completo e os comandos de rollout, veja [docs/rollout/README.md](docs/rollout/README.md) e [docs/plans/schema-per-tenant-migration-plan.md](docs/plans/schema-per-tenant-migration-plan.md).

Fluxo basico de instancia unica (suficiente para leitura local e a maioria dos testes):

1. Crie e ative o ambiente virtual.
2. Instale dependencias com `pip install -r requirements.txt`.
3. Suba o PostgreSQL local com `docker compose -f docker-compose.postgres.yml up -d`.
4. Copie `.env.example` para `.env` e ajuste o minimo necessario.
5. Mantenha `DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5433/octobox_control` para o banco Docker local padrao, ou aponte para outro PostgreSQL 15+.
6. Rode `python manage.py migrate_schemas --shared`.
7. Rode `python manage.py migrate_schemas`.
8. Rode `python manage.py bootstrap_roles` (por tenant; o `provision_box` ja faz bootstrap de roles para um box recem-provisionado).
9. Crie um usuario administrativo com `python manage.py createsuperuser`.
10. Suba o servidor com `python manage.py runserver`.
11. Rode os testes com PostgreSQL usando `python -m pytest --create-db --migrations -q`.

Observacao:

- login, logout, mudancas no admin e acoes comerciais sensiveis ja alimentam a trilha de auditoria
- para ambiente local, o projeto le automaticamente `.env` quando ele existir
- PostgreSQL e o banco padrao para desenvolvimento local, testes, homologacao e producao porque `django-tenants` depende de schemas PostgreSQL
- `python manage.py test` prefere `config.settings.test` e tambem aceita `.env.test` local como complemento opcional
- `TEST_DATABASE_URL` sobrescreve `DATABASE_URL` apenas nos testes; se ambos estiverem ausentes, as settings apontam para o PostgreSQL local padrao em `127.0.0.1:5433`
- para ambiente local, voce pode definir `DJANGO_SECRET_KEY` em um arquivo `.env` ou nas variaveis do sistema
- para ambientes que usam identidade de canal WhatsApp, defina tambem `PHONE_BLIND_INDEX_KEY`
- o projeto agora aceita `DJANGO_ENV=development` ou `DJANGO_ENV=production` para separar configuracao local de homologacao/producao
- SQLite nao e mais fallback padrao; use `OCTOBOX_ALLOW_SQLITE_FALLBACK=1` apenas para diagnosticos legados que nao precisam de tenants
- para homologacao/producao, use `DATABASE_URL` com PostgreSQL, `REDIS_URL` para cache compartilhada, rode `collectstatic` e publique atras de HTTPS
- o caminho publico do admin deve ser definido por `DJANGO_ADMIN_URL_PATH`, nao por `/admin/`
- para abrir o servidor na rede local, use a task `Run Django Server (LAN)` ou rode `python manage.py runserver 0.0.0.0:8000`
- para CI, desenvolvimento local, homologacao ou producao, use PostgreSQL 15 ou superior

Guias novos:

- deploy de homologacao: [docs/rollout/deploy-homologation.md](docs/rollout/deploy-homologation.md)
- backup minimo do banco: [docs/rollout/backup-guide.md](docs/rollout/backup-guide.md)
- baseline de seguranca de producao: [docs/reference/production-security-baseline.md](docs/reference/production-security-baseline.md)
- checklist de validacao mobile real: [docs/experience/mobile-real-validation-checklist.md](docs/experience/mobile-real-validation-checklist.md)
- scripts de backup: [scripts/backup_postgres.ps1](scripts/backup_postgres.ps1) e [scripts/restore_postgres.ps1](scripts/restore_postgres.ps1)
- deploy de producao em Hostinger VPS: [docs/rollout/hostinger-vps-production-deploy.md](docs/rollout/hostinger-vps-production-deploy.md)

## Licenca

Este projeto esta licenciado sob a GNU Affero General Public License v3.0 (AGPL-3.0). Veja [LICENSE](LICENSE).

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
