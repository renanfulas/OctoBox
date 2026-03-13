## Metadados do documento

Tipo do documento:
- estrategia de estado historico

Autoridade:
- alta para o tema de state

Documento pai:
- [architecture-growth-plan.md](architecture-growth-plan.md)

Quando usar este doc:
- quando a duvida for por que boxcore ainda existe como ancora estrutural e o que nao deve ser mexido cedo demais

## Estado atual

boxcore ainda precisa permanecer em INSTALLED_APPS porque ele ancora o estado do Django:

- migrations continuam em boxcore/migrations
- varios modelos ainda nascem via boxcore.models
- communications/model_definitions/whatsapp.py preserva app_label = 'boxcore'
- comandos e admin ainda dependem explicitamente do app config boxcore

Inventario complementar:

- veja boxcore-state-residue-inventory.md para a classificacao entre ancora estrutural e compatibilidade historica
- veja promoted-public-facades-map.md para o mapa consolidado das superficies canonicas ja promovidas no runtime

## Objetivo

Reduzir boxcore de app central para ancora temporaria de estado, sem quebrar schema, migrations nem admin, ate existir um plano seguro de saida.

## Estrategia

1. Criar superficies estaveis por app real.

- students/models.py
- finance/models.py
- operations/models.py
- auditing/models.py
- onboarding/models.py passa a isolar o lado de intake
- communications/models.py cumpre esse papel no lado de WhatsApp e reaproveita onboarding/models.py para intake

Nesta fase, os modelos continuam fisicamente ligados ao estado historico, mas os imports da aplicacao deixam de depender de boxcore.models como porta publica universal.

Estado atual dessa frente:

- o runtime da aplicacao ja nao depende mais do exportador central boxcore/models/__init__.py
- o arquivo boxcore/models/__init__.py permanece apenas como camada de compatibilidade historica para imports antigos
- o roteamento raiz HTTP tambem ja nao depende mais de boxcore.urls; config.urls passou a publicar diretamente access, api, dashboard, catalog, guide e operations
- codigo novo deve entrar pelas superficies de dominio e nao pelo exportador central

Observacao importante desta fase:

- bases abstratas e estruturas neutras de model podem sair antes do estado historico, desde que continuem sem schema proprio e sem impacto em app_label, db_table ou migrations existentes
- isso ja aconteceu com a base TimeStampedModel, que saiu de boxcore.models.base para model_support/base.py enquanto boxcore/models/base.py ficou como fachada de compatibilidade
- o mesmo criterio tambem vale para utilitarios puros sem estado do Django, como a normalizacao de telefones, agora movida para shared_support/phone_numbers.py enquanto boxcore/shared/phone_numbers.py ficou como fachada de compatibilidade
- o mesmo padrao de ownership de codigo tambem ja avancou em models concretos sensiveis sem alterar app label, como students/model_definitions.py, operations/model_definitions.py, finance/model_definitions.py, communications/model_definitions/whatsapp.py, onboarding/model_definitions.py e auditing/model_definitions.py

2. Migrar imports de aplicacao e infraestrutura para essas superficies.

Prioridade alta:

- catalog, operations, students, finance, communications, access

Prioridade media:

- dashboard, admin, management commands, testes

3. Congelar uma politica de app_label antes de qualquer split de schema.

Regra atual recomendada:

- manter app_label = 'boxcore' para modelos que ja possuem migrations historicas dependentes disso
- nao mover migrations antigas
- nao renomear o app boxcore nesta fase
- referencias historicas como 'boxcore.Student' e 'boxcore.WhatsAppContact' podem continuar em models concretos quando forem necessarias para preservar o estado atual do Django

4. Decidir o modelo de longo prazo.

Ha duas saidas viaveis:

Opcao A: boxcore continua como ancora de schema.

- apps reais concentram HTTP, services, queries e adapters
- boxcore fica cada vez mais fino
- menor risco operacional

Opcao B: split real de estado por app.

- exige plano de migracoes por dominio
- exige decisao explicita sobre db_table, app_label e dependencias entre migrations
- deve ser tratado como projeto proprio, nao como refactor oportunista

## Criterio de seguranca para remover boxcore do INSTALLED_APPS

So considerar isso quando todos os pontos abaixo forem verdadeiros:

- nenhum model ativo depender mais de app_label = 'boxcore'
- migrations historicas estiverem estabilizadas com estrategia clara de continuidade
- admin e management commands nao dependerem mais do app config boxcore
- imports de aplicacao nao usarem mais boxcore.models como porta publica

Hoje esse criterio ainda nao foi atendido.