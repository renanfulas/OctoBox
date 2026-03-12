<!--
ARQUIVO: plano pragmatico para quebrar o boxcore em apps Django reais.

POR QUE ELE EXISTE:
- Define um caminho seguro para sair do app unico sem entrar em cirurgia cara e desnecessaria cedo demais.
- Separa o que da para fazer agora com custo baixissimo do que ja exige refactor estrutural de medio custo.

O QUE ESTE ARQUIVO FAZ:
1. Desenha a arquitetura alvo por apps reais.
2. Organiza a transicao em ondas de baixo e medio custo.
3. Define regras para evitar retrabalho enquanto a migracao acontece.

PONTOS CRITICOS:
- A quebra deve preservar migrations, imports, admin, permissoes e testes.
- O objetivo e reduzir risco arquitetural, nao fazer renomeacao cosmetica em massa.
-->

# Plano de split em apps Django reais

## Tese

Hoje o projeto tem boa separacao interna por dominio, mas ainda vive dentro de um unico app Django: `boxcore`.

Isso foi suficiente para ganhar velocidade no inicio. Nao e a melhor forma de sustentar um produto grande por muito tempo.

O alvo arquitetural melhor e este:

```text
access/
auditing/
students/
finance/
operations/
communications/
onboarding/
dashboard/
guide/
api/
integrations/
jobs/
core/
```

Nem tudo precisa nascer no mesmo dia. O certo e quebrar por ondas, com custo controlado.

## O que significa sucesso

O split esta dando certo quando:

1. cada dominio passa a ter dono tecnico claro
2. imports ficam mais previsiveis
3. urls, admin, sinais e testes ficam agrupados por dominio real
4. integrar API, webhook e jobs para de depender do miolo web
5. a chance de tocar em cinco areas ao mesmo tempo para uma feature simples diminui

## O que nao fazer

1. mover tudo de uma vez
2. trocar app labels de modelos sensiveis cedo demais
3. quebrar migrations historicas sem necessidade real
4. fazer split por vaidade visual sem reduzir acoplamento de verdade

## Arquitetura alvo pragmatica

### Apps de fundacao

- `core`: bases compartilhadas de modelo, utilitarios estruturais e pontos realmente transversais
- `access`: login, papeis, permissoes, navegacao global
- `auditing`: eventos, servicos e sinais de auditoria

### Apps de negocio

- `students`: cadastro principal do aluno e perfil
- `onboarding`: intake e entradas provisiorias
- `finance`: planos, matriculas, pagamentos, relatorios financeiros
- `operations`: aulas, presenca, ocorrencias e acoes de rotina
- `communications`: contatos e logs de WhatsApp, identidade de canal e comunicacao operacional

### Apps de composicao

- `dashboard`: painel consolidado
- `guide`: mapa interno do sistema

### Apps de fronteira

- `api`: contratos externos e endpoints versionados
- `integrations`: provedores externos, webhooks, adaptadores
- `jobs`: tarefas assincronas e automacoes

## Mapa do que existe hoje para onde deve ir

| Hoje | App alvo |
|---|---|
| `boxcore/access/` | `access/` |
| `boxcore/auditing/` + `boxcore/models/audit.py` | `auditing/` |
| `boxcore/models/students.py` | `students/` |
| `boxcore/models/onboarding.py` | `onboarding/` |
| `boxcore/models/finance.py` + `boxcore/catalog/finance_snapshot/` | `finance/` |
| `boxcore/models/communications.py` + `boxcore/integrations/whatsapp/` | `communications/` e `integrations/` |
| `boxcore/models/operations.py` + `boxcore/operations/` | `operations/` |
| `boxcore/dashboard/` | `dashboard/` |
| `boxcore/guide/` | `guide/` |
| `boxcore/api/` | `api/` |
| `boxcore/jobs/` | `jobs/` |

## Baixissimo custo: o que da para fazer agora

Estas acoes quase nao mexem em comportamento e ja colocam o projeto no trilho certo.

### 1. Congelar a arquitetura alvo por escrito

Ja vale fazer agora porque reduz improviso.

Entregas:

1. este documento
2. ligacao com o plano arquitetural maior
3. regra explicita de ondas de migracao

### 2. Preparar o settings para apps multiplos

Mesmo antes de criar apps reais, vale separar:

1. `DJANGO_APPS`
2. `LOCAL_APPS`
3. no futuro, se quiser, `THIRD_PARTY_APPS`

Isso parece pequeno, mas deixa a mudanca de `INSTALLED_APPS` muito menos baguncada.

### 3. Parar de criar codigo novo em lugares errados

Regra nova para a base:

1. tudo que for API nova entra com mentalidade de app `api`
2. tudo que for webhook ou provider entra com mentalidade de app `integrations`
3. tudo que for tarefa futura entra com mentalidade de app `jobs`
4. nao colocar regra nova diretamente em `boxcore/models/__init__.py`

Ou seja: antes do split fisico, o split mental ja precisa estar valendo.

### 4. Reduzir dependencias cruzadas do monolito

Baixo custo e alto retorno:

1. preferir importar do modulo de dominio real, nao de agregadores gigantes
2. continuar mantendo fachadas de compatibilidade so onde fizer sentido
3. evitar que dashboard e guide virem donos de regra

### 5. Definir ordem oficial da migracao

Melhor sequencia de risco baixo:

1. `api`
2. `jobs`
3. `integrations`
4. `access`
5. `auditing`
6. `communications`

Esses seis sao os melhores candidatos iniciais porque ou ja sao fronteiras naturais, ou ja estao relativamente isolados.

## Medio custo: o que vale fazer depois

Aqui ja existe refactor real, mas ainda com risco controlado se for por ondas.

### Onda 1: transformar fronteiras em apps Django reais

Criar apps reais para:

1. `api`
2. `jobs`
3. `integrations`

Por que comecar aqui:

1. quase nao dependem de modelo historico pesado
2. reforcam a arquitetura de crescimento
3. ajudam mobile, webhook e tarefas futuras sem tocar forte no core atual

O que fazer:

1. criar `AppConfig` proprio
2. mover urls, views e modulos ja criados
3. ajustar `INSTALLED_APPS`
4. manter imports antigos como casca temporaria se necessario

### Onda 2: extrair `access` e `auditing`

Esses dois apps costumam compensar cedo.

Por que:

1. concentram responsabilidade clara
2. reduzem o peso institucional do `boxcore`
3. ajudam a organizar permissao, sinais e rastreabilidade

Cuidados:

1. sinais no startup
2. imports de papeis e context processor
3. admin e testes de acesso

Status atual:

1. `access/` e `auditing/` ja existem como apps reais instalados
2. `boxcore/access/` e `boxcore/auditing/` ficaram como fachadas de compatibilidade
3. `boxcore/urls.py` e o context processor global ja apontam para os apps novos
4. a extracao de `communications` continua separada por custo, porque ainda toca modelo historico e fluxos cruzados

### Onda 3: extrair `communications`

Esse app merece vida propria porque sera ponte entre aluno, canal, webhook e comunicacao operacional.

Por que e medio custo:

1. toca modelo
2. conversa com onboarding
3. conversa com integracoes
4. conversa com catalogo financeiro

Cuidados:

1. manter compatibilidade com modelo atual antes de trocar app label
2. preservar migrations historicas
3. nao misturar provider externo com modelo interno do canal

Status atual:

1. `communications/` ja existe como app real instalado
2. services e queries de comunicacao ja sairam de `boxcore/catalog/services/communications.py` e de leituras operacionais espalhadas
3. integracoes WhatsApp ja importam a superficie publica de `communications.models`
4. os modelos continuam fisicamente em `boxcore.models` nesta fase para preservar migrations e app label
5. o admin do dominio agora vive em `communications/admin.py`, com `boxcore/admin/onboarding.py` funcionando como fachada legada
6. leituras restantes de intake e WhatsApp no catalogo passaram a importar a superficie publica de `communications`
7. o plano tecnico da fase sensivel de models foi congelado em `docs/communications-model-split-blueprint.md`

### Onda 4: extrair `students`, `onboarding`, `finance` e `operations`

Essa ja e a parte mais sensivel.

Aqui mora a maior parte do dominio e das migrations historicas.

Por isso o melhor caminho nao e mover tudo direto. O ideal e:

1. primeiro extrair services, queries, forms, urls e admin
2. depois avaliar a migracao de modelos com muito cuidado
3. usar fases com fachadas de compatibilidade

## Estrategia tecnica recomendada

### Regra 1: separar modulo primeiro, modelo depois

Primeiro mova:

1. urls
2. views
3. services
4. queries
5. forms
6. admin
7. tests

So depois pense em mover modelos de app label, porque isso e onde o custo explode.

### Regra 2: preservar import path durante a transicao

Exemplo mental:

1. o codigo real passa a morar em `finance/`
2. `boxcore/catalog/...` vira casca temporaria
3. quando tudo estiver estabilizado, a casca pode morrer

### Regra 3: nao mexer cedo em migrations historicas

Enquanto nao houver necessidade real, prefira:

1. manter modelo no app label antigo
2. mover somente a organizacao do codigo Python
3. adiar renomeacoes profundas de app/model label

### Regra 4: medir custo por dominio

#### Baixo risco de extracao

1. `api`
2. `jobs`
3. `integrations`
4. `guide`

#### Medio risco de extracao

1. `access`
2. `auditing`
3. `communications`
4. `dashboard`

#### Alto risco de extracao

1. `students`
2. `onboarding`
3. `finance`
4. `operations`

## Primeira linha de acao recomendada

Se a pergunta for “por onde comecar sem doer”, eu faria assim:

### Agora

1. manter este plano como referencia oficial
2. preparar `INSTALLED_APPS` para apps multiplos
3. adotar a regra de nao criar mais codigo novo pensando em `boxcore` como dono definitivo

### Proximo passo de medio custo

1. criar os apps reais `api`, `jobs` e `integrations`
2. mover o codigo que ja existe nessas fronteiras
3. validar testes
4. executar a ordem detalhada em [wave-1-app-blueprint.md](wave-1-app-blueprint.md)

### Depois

1. extrair `access`
2. extrair `auditing`
3. extrair `communications`

## Decisao final

Sim, a arquitetura por apps reais e melhor do que deixar tudo para sempre dentro de `boxcore`.

Mas o melhor caminho nao e uma grande reescrita. O melhor caminho e:

1. definir o mapa
2. preparar o terreno
3. migrar fronteiras primeiro
4. deixar os modelos mais pesados por ultimo

Isso custa pouco agora, melhora a clareza ja, e evita uma cirurgia cara antes da hora.