<!--
ARQUIVO: blueprint tecnico para a fase sensivel de migracao dos modelos de communications.

POR QUE ELE EXISTE:
- Traduz a parte mais arriscada da migracao em uma sequencia tecnica defensavel.
- Evita improviso ao lidar com app label, content types, permissoes, admin URLs e migrations historicas.

O QUE ESTE ARQUIVO FAZ:
1. Define o alvo real dos modelos do dominio communications.
2. Explica a estrategia recomendada sem reescrever migrations antigas.
3. Lista ordem de implementacao, riscos, rollback e validacoes.

PONTOS CRITICOS:
- O historico de migrations de communications nasceu em boxcore e nao deve ser reescrito.
- Trocar app label muda content types, permissoes, nomes de rotas do admin e referencias internas do Django.
-->

# Blueprint tecnico da migracao dos modelos de communications

## Objetivo

Mover a posse real dos modelos ligados a WhatsApp e comunicacao operacional para fora de boxcore sem quebrar:

1. migrations historicas ja aplicadas
2. restauracoes antigas de banco
3. content types e permissoes do Django
4. nomes de rotas do admin usados pela navegacao e por testes
5. imports antigos durante a transicao

## Escopo real desta fase

### Modelos que pertencem ao dominio communications

1. `WhatsAppContact`
2. `WhatsAppMessageLog`
3. `WhatsAppContactStatus`
4. `MessageDirection`
5. `MessageKind`

### Modelos que parecem proximos, mas nao devem migrar junto agora

1. `StudentIntake`
2. `IntakeSource`
3. `IntakeStatus`

Motivo:

1. `StudentIntake` e staging comercial e onboarding, nao comunicacao de canal pura.
2. misturar intake com WhatsApp na mesma migracao aumenta risco desnecessariamente.
3. o alvo final mais coerente para intake e um app `onboarding`, nao `communications`.

## Estado atual do projeto

Hoje a base ja fez o movimento de ownership de codigo, mas nao o movimento de estado do Django:

1. o app real [communications](../communications) ja existe
2. services e queries ja moram em [communications/services.py](../communications/services.py) e [communications/queries.py](../communications/queries.py)
3. o admin do dominio ja mora em [communications/admin.py](../communications/admin.py)
4. a superficie publica transitória dos modelos mora em [communications/models.py](../communications/models.py)
5. os modelos reais ainda vivem em [boxcore/models/communications.py](../boxcore/models/communications.py)
6. `StudentIntake` ainda vive em [boxcore/models/onboarding.py](../boxcore/models/onboarding.py)
7. as migrations historicas continuam em [boxcore/migrations/0002_studentintake_whatsappcontact_whatsappmessagelog.py](../boxcore/migrations/0002_studentintake_whatsappcontact_whatsappmessagelog.py) e [boxcore/migrations/0006_integration_hardening.py](../boxcore/migrations/0006_integration_hardening.py)

## O que torna esta fase sensivel

O problema nao e mover arquivo Python. O problema e o estado interno do Django.

Quando um model muda de app label, mudam junto:

1. `ContentType.app_label`
2. permissoes padrao do model
3. nomes de rotas do admin
4. nomes padrao de tabela, se `db_table` nao estiver congelado
5. relacionamento historico do grafo de migrations

Exemplos concretos desta base:

1. hoje as tabelas historicas nasceram como `boxcore_whatsappcontact` e `boxcore_whatsappmessagelog`
2. hoje o admin aponta para caminhos como `/admin/boxcore/whatsappcontact/`
3. hoje as permissoes de grupo usam codenames ligados ao content type do app `boxcore`
4. hoje as migrations antigas referenciam `boxcore.whatsappcontact` e `boxcore.whatsappmessagelog`

## Decisao tecnica recomendada

### Recomendacao principal

Fazer em duas etapas distintas, e nao em um salto unico.

### Etapa A: mover a implementacao Python, manter app label `boxcore`

Objetivo:

1. tirar a implementacao real de [boxcore/models/communications.py](../boxcore/models/communications.py)
2. manter o estado do Django identico
3. nao gerar migration de banco
4. nao mudar admin URL
5. nao mudar permission codename nem content type ainda

Como fica:

1. a definicao real da classe passa a morar em algo como `communications/model_definitions/whatsapp.py`
2. cada model passa a declarar `class Meta: app_label = 'boxcore'`
3. [boxcore/models/communications.py](../boxcore/models/communications.py) vira fachada importando a definicao real
4. [communications/models.py](../communications/models.py) continua sendo a superficie publica preferida

Resultado:

1. ownership de codigo sai de boxcore
2. o Django continua enxergando esses models como `boxcore`
3. risco operacional fica baixo

### Etapa B: decidir se vale mesmo trocar o app label para `communications`

Essa etapa e opcional e so deve acontecer se o beneficio real compensar o custo.

Motivo:

1. boa parte do ganho arquitetural ja aparece na etapa A
2. a troca real de app label e a parte mais cara de toda a migracao
3. se o produto continuar evoluindo bem com ownership de codigo fora de boxcore, talvez a troca de label nem compense cedo

## Quando a troca real de app label faz sentido

So vale seguir para a etapa B se pelo menos estas condicoes estiverem verdadeiras:

1. quase todo o codigo ja importar de `communications.models`, e nao de `boxcore.models`
2. admin, docs, guide e testes ja nao dependerem de nomes `boxcore_*`
3. o time aceitar uma migracao de content types e permissoes
4. houver tempo para rollout, auditoria e rollback bem controlados

## Sequencia recomendada da Etapa A

### Passo 1: congelar contratos de banco e identidade

Antes de mover a implementacao real:

1. adicionar `db_table` explicito nos models de WhatsApp
2. manter nomes de constraints exatamente como estao
3. nao alterar `related_name`
4. nao alterar campos, tipos nem defaults

Tabela alvo que deve permanecer:

1. `boxcore_whatsappcontact`
2. `boxcore_whatsappmessagelog`

### Passo 2: criar modulo de implementacao real fora de boxcore

Exemplo de destino:

1. `communications/model_definitions/__init__.py`
2. `communications/model_definitions/whatsapp.py`

Conteudo esperado:

1. `WhatsAppContactStatus`
2. `MessageDirection`
3. `MessageKind`
4. `WhatsAppContact`
5. `WhatsAppMessageLog`

Com regra explicita:

1. `Meta.app_label = 'boxcore'`
2. `Meta.db_table` fixo

### Passo 3: transformar [boxcore/models/communications.py](../boxcore/models/communications.py) em fachada

Esse arquivo deve apenas reexportar as classes reais.

Objetivo:

1. preservar imports antigos
2. manter compatibilidade com migrations historicas
3. reduzir risco em uma release so

### Passo 4: manter [communications/models.py](../communications/models.py) como superficie publica unica

Depois disso, a regra da base deve ficar clara:

1. codigo novo importa de `communications.models`
2. imports antigos de `boxcore.models` viram passivo tecnico a ser reduzido

### Passo 5: validar que nenhuma migration nova foi gerada por acidente

Check obrigatorio:

1. `makemigrations --check`
2. `manage.py check`
3. suites de integrations, catalog, catalog_services, guide e operations

## Sequencia recomendada da Etapa B

So execute esta etapa se a decisao de trocar o app label estiver tomada.

### Passo 1: reduzir dependencias de nome legado

Antes da troca real:

1. remover referencias hardcoded a `/admin/boxcore/whatsappcontact/`
2. trocar reverses e docs que assumem `admin:boxcore_whatsappcontact_*`
3. parar de usar `boxcore.models` nos pontos ligados ao dominio communications

### Passo 2: criar migrations de estado, nao de banco

Estrutura recomendada:

1. criar migration em `communications` com `SeparateDatabaseAndState`
2. nessa migration, adicionar os models ao estado do app `communications`
3. apontar `db_table` para as tabelas ja existentes
4. nao executar `CreateModel` real no banco

Depois:

1. criar migration em `boxcore` removendo os models apenas do estado
2. tambem via `SeparateDatabaseAndState`
3. sem `DROP TABLE`

Objetivo:

1. o banco continua igual
2. o estado do Django muda de `boxcore` para `communications`

### Passo 3: migrar content types e permissoes

Esse passo e obrigatorio se o app label mudar.

Precisa fazer:

1. data migration ou comando idempotente que copie ou remapeie permissoes de `boxcore` para `communications`
2. atualizar grupos existentes para os novos content types
3. revisar se o admin continua exibindo os modelos esperados

### Passo 4: revisar admin URLs e navegacao

Impacto esperado:

1. o Django admin passa a gerar URLs `admin:communications_whatsappcontact_*`
2. links hardcoded antigos quebram se nao forem migrados

Arquivos candidatos a ajuste:

1. [access/context_processors.py](../access/context_processors.py)
2. [boxcore/guide/views.py](../boxcore/guide/views.py)
3. docs e testes que mencionem `boxcore` no admin

### Passo 5: revisar sinais, auditoria e testes

Checar:

1. rastreabilidade no admin
2. integracoes inbound e outbound
3. tela de alunos e fila operacional
4. leitura de dashboard e operations

## O que nao fazer

1. editar [boxcore/migrations/0002_studentintake_whatsappcontact_whatsappmessagelog.py](../boxcore/migrations/0002_studentintake_whatsappcontact_whatsappmessagelog.py)
2. editar [boxcore/migrations/0006_integration_hardening.py](../boxcore/migrations/0006_integration_hardening.py)
3. trocar `StudentIntake` de app junto com WhatsApp nesta mesma fase
4. mudar tabela e app label na mesma release sem fase intermediaria
5. confiar que o Django vai “entender sozinho” a mudanca de ownership sem migrations de estado

## Ordem de rollout recomendada

### Release 1

1. congelar `db_table`
2. mover a implementacao real para fora de boxcore
3. manter `app_label = 'boxcore'`
4. validar ausencia de migration estrutural

### Release 2

1. reduzir imports legados e hardcodes de admin
2. medir se ainda existe necessidade real de trocar o app label

### Release 3

1. se fizer sentido, executar a migracao de estado para `communications`
2. migrar content types, permissoes e rotas de admin relacionadas

## Rollback

### Se a falha ocorrer na Etapa A

Rollback simples:

1. voltar a fachada de [boxcore/models/communications.py](../boxcore/models/communications.py) para implementacao local
2. nenhuma migration de banco precisa ser revertida

### Se a falha ocorrer na Etapa B

Rollback mais sensivel:

1. reverter migrations de estado em ordem inversa
2. restaurar content types e permissoes antigos se ja tiverem sido migrados
3. confirmar que o admin voltou a usar o namespace anterior

## Matriz minima de validacao

### Tecnica

1. `manage.py check`
2. `manage.py makemigrations --check`
3. `manage.py test boxcore.tests.test_integrations --verbosity 0`
4. `manage.py test boxcore.tests.test_catalog_services --verbosity 0`
5. `manage.py test boxcore.tests.test_catalog --verbosity 0`
6. `manage.py test boxcore.tests.test_operations --verbosity 0`
7. `manage.py test boxcore.tests.test_guide --verbosity 0`

### Funcional

1. criar contato inbound via integracao WhatsApp
2. registrar toque operacional outbound
3. abrir admin de intake
4. abrir admin de contato WhatsApp
5. abrir admin de log de mensagem
6. validar queue e snapshots que mostram intakes e contatos

## Decisao final recomendada hoje

Hoje, a melhor decisao tecnica e esta:

1. executar primeiro a Etapa A
2. manter `StudentIntake` fora desta migracao
3. adiar a troca real de app label para um momento em que imports, admin URLs e permissoes estejam mais limpos

Em termos práticos:

1. o proximo passo seguro nao e “migrar o banco”
2. o proximo passo seguro e “migrar a implementacao real do model para fora de boxcore mantendo o estado do Django igual”

Isso entrega a maior parte do ganho arquitetural com o menor risco operacional.
