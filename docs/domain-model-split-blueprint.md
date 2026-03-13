## Objetivo

Definir o primeiro blueprint real para sair do estado atual, onde boxcore ainda ancora models e migrations, comparando duas rotas possíveis:

1. manter boxcore como âncora de schema
2. planejar uma migração formal de app_label por ondas

Esse documento existe para evitar um erro clássico: continuar refatorando imports e apps HTTP sem decidir conscientemente qual será o destino do estado de models.

## Estado atual

Hoje a arquitetura já avançou bastante fora de boxcore:

- access, auditing, communications, integrations, jobs, operations e catalog já existem como apps reais
- students e finance já existem como apps leves
- há superfícies estáveis de models em students/models.py, finance/models.py, operations/models.py, auditing/models.py e onboarding/models.py
- a maior parte da casca HTTP e da orquestração nova já não nasce em boxcore

Mas o estado de models ainda depende fortemente de boxcore:

- migrations históricas continuam em boxcore/migrations
- boxcore/apps.py ainda é o app config que ancora esse estado
- communications/model_definitions/whatsapp.py preserva app_label = 'boxcore'
- parte do admin e comandos internos ainda orbitam esse estado

## Rota A

### boxcore como âncora de schema

### ideia

Assumir explicitamente que boxcore deixa de ser centro de aplicação, mas continua sendo o contêiner do estado histórico dos models.

### como funciona

- apps reais continuam absorvendo HTTP, queries, services, adapters e contratos
- imports de aplicação passam a usar superfícies por domínio, não boxcore.models
- models concretos continuam ligados ao estado histórico de boxcore
- boxcore vira um app fino de compatibilidade, migrations e admin residual

### vantagens

- menor risco operacional
- não exige reescrever o histórico de migrations
- reduz muito a chance de drift de schema ou quebra de ambientes existentes
- combina bem com a estratégia incremental que o projeto já vem seguindo

### custos

- boxcore nunca desaparece completamente do estado do Django
- o nome histórico continua presente em admin, migrations e algumas referências internas
- há um limite estrutural para o desacoplamento total

### quando escolher

- quando a prioridade for estabilidade de produto
- quando o valor maior estiver em separar fronteiras de código e operação, não em renomear o estado do banco
- quando não existir demanda forte para independência formal de schema por domínio

## Rota B

### migração formal de app_label por ondas

### ideia

Mover o estado real dos models de boxcore para apps de domínio, com app_label e continuidade de migrations próprios.

### como funciona

- cada domínio recebe um plano explícito de migração de estado
- modelos passam a ter novo app_label por domínio
- o histórico de migrations passa a ser tratado como projeto de infraestrutura, não como refactor comum
- o admin e os comandos deixam de apontar para boxcore gradualmente

### vantagens

- separação estrutural completa entre domínios
- boxcore pode, no limite, sair do INSTALLED_APPS no futuro
- o projeto fica mais alinhado com uma arquitetura multi-app “pura” no Django

### custos

- risco alto se mal executado
- exige estratégia por domínio para db_table, dependências entre migrations, content types e admin
- impacta ambientes existentes, backups, restore e eventualmente automações externas
- não é trabalho oportunista; é trilha própria de migração

### quando escolher

- quando houver benefício real de produto, governança ou operação que justifique o risco
- quando o time aceitar tratar isso como projeto dedicado
- quando houver janela para validar a migração em staging, snapshots e restore com disciplina

## Comparação objetiva

### estabilidade

- Rota A vence claramente

### pureza arquitetural

- Rota B vence claramente

### custo de execução

- Rota A é muito mais barata

### risco de regressão

- Rota B é muito mais arriscada

### aderência ao caminho já seguido no projeto

- Rota A é a continuação natural do que já foi feito

## Recomendação atual

Para o estado atual do projeto, a recomendação é seguir com a Rota A como padrão de curto e médio prazo.

Isso significa:

- continuar promovendo apps reais e superfícies estáveis de domínio
- continuar reduzindo imports diretos de boxcore.models
- continuar deixando boxcore cada vez mais fino
- não mexer ainda em app_label e migrations históricas

A Rota B deve existir como possibilidade futura, mas só deve começar quando houver um blueprint específico por domínio e motivação clara para pagar esse custo.

## Pré-requisitos mínimos antes de considerar a Rota B

1. Quase nenhum código de aplicação deve depender mais de boxcore.models como porta pública.
2. Cada domínio precisa ter superfície estável própria de models e imports consolidados.
3. Admin e management commands precisam estar desacoplados do app config boxcore.
4. O projeto precisa ter rotina confiável de backup, restore e validação de migrations.
5. A migração deve ser desenhada por domínio, não “big bang”.

## Ordem sugerida se um dia a Rota B for escolhida

1. auditing
2. operations
3. finance
4. students
5. communications/onboarding

Essa ordem prioriza domínios mais previsíveis e deixa os mais sensíveis para depois.

## Próximos passos recomendados agora

1. continuar trocando imports de boxcore.models para superfícies por domínio
2. reduzir dependência de boxcore no admin e nos management commands restantes
3. manter boxcore como âncora de schema por enquanto, sem vergonha arquitetural nisso
4. revisitar a decisão de split real de estado só quando o código de aplicação já estiver majoritariamente desacoplado