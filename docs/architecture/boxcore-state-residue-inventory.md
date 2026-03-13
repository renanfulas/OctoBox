## Metadados do documento

Tipo do documento:
- inventario de referencia arquitetural

Autoridade:
- media

Documento pai:
- [boxcore-model-state-plan.md](boxcore-model-state-plan.md)

Quando usar este doc:
- quando a duvida for onde boxcore ainda pesa de verdade e qual resíduo e estrutural versus apenas psicologico

## Objetivo

Mapear o que ainda depende do estado historico de boxcore e separar dois grupos:

- o que e estrutural e precisa ficar por enquanto
- o que e apenas compatibilidade e pode sair em cortes futuros sem mexer no schema

## Estado formal atual

Depois dos ultimos cortes, boxcore deve ser lido como um app legado de estado do Django.

Na pratica isso significa:

- continua sendo ancora historica de app config, app_label e migrations
- nao deve mais ser tratado como raiz canonica de runtime HTTP
- nao deve ser a primeira opcao para codigo novo fora dos pontos estruturais listados abaixo

## Residuos estruturais que precisam ficar por enquanto

### 1. boxcore ainda ancora o app state do Django

Arquivos principais:

- config/settings/base.py
- boxcore/apps.py

Motivo:

- boxcore continua em INSTALLED_APPS
- o app config oficial ainda e boxcore
- remover isso agora faria o Django perder o anchor do estado historico antes de existir uma estrategia nova para migrations e labels

Conclusao:

- nao e removivel agora

### 2. migrations historicas continuam pertencendo a boxcore

Arquivos principais:

- boxcore/migrations/0001_initial.py
- boxcore/migrations/0002_studentintake_whatsappcontact_whatsappmessagelog.py
- boxcore/migrations/0006_integration_hardening.py

Motivo:

- as migrations referenciam modelos via boxcore
- ha uso direto de apps.get_model('boxcore', ...)
- mover ou reescrever migrations antigas agora aumentaria risco sem ganho proporcional

Conclusao:

- e ancora estrutural
- nao deve ser mexido nesta fase

### 3. models concretos de WhatsApp ainda preservam o label historico

Arquivo principal:

- communications/model_definitions/whatsapp.py

Motivo:

- os models concretos usam HISTORICAL_BOXCORE_APP_LABEL
- os relacionamentos ainda apontam para HISTORICAL_BOXCORE_STUDENT_MODEL e HISTORICAL_BOXCORE_WHATSAPP_CONTACT_MODEL
- isso preserva schema, relacoes e compatibilidade com migrations existentes

Conclusao:

- e estrutural por enquanto
- o ownership do codigo ja saiu de boxcore, mas o ownership do estado ainda nao

### 4. superficies publicas de model ainda reexportam a partir de boxcore.models

Arquivos principais:

- students/models.py
- finance/models.py
- operations/models.py
- auditing/models.py
- onboarding/models.py

Motivo:

- essas superficies ja resolveram o acoplamento de importacao da aplicacao
- mas ainda dependem dos models concretos historicos definidos em boxcore
- tirar esse vinculo sem um plano de split de estado exigiria mudar onde os modelos realmente nascem

Conclusao:

- e dependencia estrutural transitoria
- nao e o proximo corte mais seguro

## Residuos de compatibilidade que ainda existem por causa do app label historico

### 5. namespace do admin continua em boxcore

Arquivos principais:

- access/context_processors.py
- boxcore/tests/test_audit.py
- communications/admin.py
- students/admin.py
- finance/admin.py
- operations/admin.py
- auditing/admin.py

Motivo:

- os registros administrativos reais ja foram movidos para apps de dominio
- mas as URLs e nomes do admin continuam resolvendo no namespace boxcore porque o app label dos modelos ainda e historico

Conclusao:

- nao e a raiz do problema
- esse resíduo desaparece naturalmente quando o estado dos modelos deixar de depender de boxcore

### 6. fachadas e imports legados continuam existindo para estabilidade

Exemplos:

- boxcore/models/base.py
- boxcore/models/communications.py
- boxcore/admin/*.py

Motivo:

- essas fachadas evitam quebra em imports e mantem a transicao incremental
- elas ja nao concentram a implementacao real mais sensivel

Conclusao:

- sao compatibilidade util
- podem ser reduzidas mais tarde, mas nao vale atacar antes do estado estrutural

## O que ja nao parece mais problema real

- imports de aplicacao e testes para boxcore.models foram reduzidos de forma ampla
- o ownership do codigo de communications ja saiu parcialmente de boxcore
- a base abstrata TimeStampedModel ja foi neutralizada sem efeito colateral no schema

## Classificacao pratica

### Fica agora

- boxcore em INSTALLED_APPS
- boxcore/apps.py como app config historico
- migrations em boxcore/migrations
- app_label e ForeignKey historicos em communications/model_definitions/whatsapp.py
- reexports de superficies de model que ainda apontam para boxcore.models

### Nao vale atacar antes disso

- nomes de URL do admin com prefixo boxcore
- fachadas legadas de admin e models
- comentarios e docs que apenas descrevem o estado historico

## Leitura tecnica do estado atual

O projeto ja nao sofre mais de dependencia difusa de boxcore no runtime. O que sobrou esta concentrado em um pequeno conjunto de pontos de state anchor do Django.

Em outras palavras:

- antes o problema era espalhamento
- agora o problema e ownership formal de schema, app_label e migrations

## Proximo corte seguro recomendado

O proximo passo mais seguro nao e remover boxcore do app state. E mapear model por model qual deles ainda nasce de fato em boxcore e qual deles ja tem ownership de codigo fora dele.

Matriz comparativa complementar:

- veja domain-model-ownership-matrix.md para a visao por dominio entre ownership de codigo e ownership de estado

Prioridade sugerida:

1. fechar esse mapa para students, finance, operations, auditing e onboarding
2. manter communications/whatsapp como referencia do padrao de transicao
3. so depois discutir se algum dominio merece um plano proprio de split de estado