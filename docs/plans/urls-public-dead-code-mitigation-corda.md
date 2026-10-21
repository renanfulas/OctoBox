<!--
ARQUIVO: C.O.R.D.A. de mitigacao do config/urls_public.py morto.

TIPO DE DOCUMENTO:
- plano de decisao arquitetural pequena (nao e bugfix de producao — nada quebra hoje)

AUTORIDADE:
- alta para a pergunta "o que fazer com urls_public.py / PUBLIC_SCHEMA_URLCONF"
- baixa para qualquer outro assunto de tenancy/roteamento

DOCUMENTOS PAI:
- [student-login-magic-link-bugs-corda.md](student-login-magic-link-bugs-corda.md) (REVISAO 6) — onde o achado apareceu pela primeira vez, investigando uma pergunta separada ("login em porta/servico dedicado")

QUANDO USAR:
- antes de mexer em `config/urls_public.py`, `PUBLIC_SCHEMA_URLCONF` ou em `control.middleware.TenantBySessionMiddleware.PUBLIC_SCHEMA_PATHS`
- quando alguem propuser "separar login numa porta/servico proprio" — leia a Secao C antes de desenhar isso do zero

POR QUE ELE EXISTE:
- `config/urls_public.py` afirma, no proprio docstring (antes desta revisao), que o runtime troca de urlconf por schema. Isso e falso hoje. Um agente ou dev que confiar nesse docstring vai editar um arquivo morto e nao entender por que nada mudou em producao — exatamente o tipo de armadilha que "com certeza vamos esquecer" (motivo pelo qual este doc existe).
- registra as 3 saidas possiveis (reativar de verdade / reaproveitar como contrato / excluir) com risco de cada uma, pra decisao nao virar chute.

O QUE ESTE ARQUIVO FAZ:
1. explica por que o arquivo esta morto, com evidencia (nao suposicao).
2. avalia 3 mitigacoes possiveis, cada uma com risco real levantado por leitura de codigo.
3. recomenda uma, registra por que as outras nao foram escolhidas agora.

PONTOS CRITICOS:
- nenhuma das 3 mitigacoes foi executada ainda. Este documento e o plano, nao o resultado.
- `config/urls_public.py` e `CLAUDE.md` ja foram corrigidos para nao mentir sobre o comportamento atual (isso NAO e a mitigacao completa, e so parar a sangria da desinformacao).
-->

# C.O.R.D.A. - Mitigação do `config/urls_public.py` morto

## C - Contexto

Investigando o pedido "o login precisa ser uma janela separada, em outra porta" (docs/plans/student-login-magic-link-bugs-corda.md, REVISAO 6), descobri por leitura de código — depois confirmada rodando o servidor de verdade — que:

1. `config/settings/base.py:477` define `PUBLIC_SCHEMA_URLCONF = 'config.urls_public'`.
2. `django_tenants.middleware.TenantMainMiddleware` — o **único** componente do django-tenants que leria essa setting e trocaria `request.urlconf` — **não está em `MIDDLEWARE`** (`config/settings/base.py:423-460`). `django_tenants` só aparece como app (`SHARED_APPS`, para ORM/migrations) e como `DATABASE_ROUTERS`.
3. `ROOT_URLCONF = 'config.urls'` (`base.py:485`) é o único urlconf que qualquer request real usa — confirmado testando ao vivo: uma rota nova adicionada só a `urls_public.py` retornava 404 (`Resolver404`) num servidor rodando, enquanto a mesma rota em `config/urls.py` funcionava.
4. Toda rota de `urls_public.py` **já existe** em `config/urls.py`, geralmente com implementação mais completa:

| Rota em `urls_public.py` | Equivalente real em `config/urls.py` |
|---|---|
| `login/` → `auth_views.LoginView` | `access.urls` → `AccessEntryHubView` (+ `login/funcionario/`, `login/senha/*` — fluxo mais completo) |
| `logout/` → `auth_views.LogoutView` | `access.urls` → `LogoutView` (mesma view) |
| `include('signup.urls')` | idêntico, incluído também em `config/urls.py` |
| `include('integrations.urls')` | idêntico |
| `api/` → `include('api.urls')` | idêntico |
| `aluno/` → `include('student_app.urls')` | idêntico |
| `metrics/` | idêntico |
| `settings.ADMIN_URL_PATH` → `admin.site.urls` | idêntico |

5. A isolação real de "essa rota funciona sem tenant/login" é feita por **outro mecanismo, que funciona e é testado**: `control.middleware.TenantBySessionMiddleware.PUBLIC_SCHEMA_PATHS` — uma whitelist de prefixo de *path* (não de domínio, não de porta) que força `connection.set_schema_to_public()` para requests cujo path bate com a lista, independente de qual domínio/porta resolveu a request.

**Não é bug de produção.** Nada quebra hoje porque `config/urls.py` sempre cobriu essas rotas. O problema é só o **docstring mentiroso** (já corrigido nesta sessão) e a **setting morta** (`PUBLIC_SCHEMA_URLCONF`, ainda não removida) — ambos convidam um dev/agente futuro a perder tempo editando um arquivo sem efeito, ou pior, a assumir uma garantia de isolamento por domínio que não existe.

## O - Objetivo

1. parar de mentir sobre o comportamento do sistema (feito: docstring + CLAUDE.md corrigidos nesta revisão).
2. decidir e registrar **uma** das 3 mitigações abaixo — não deixar a pergunta em aberto pra sempre.
3. se a mitigação escolhida envolver mexer em `TenantBySessionMiddleware`/`PUBLIC_SCHEMA_PATHS`, fazer isso sem regressão — esse middleware tem histórico de bugs sutis já corrigidos (ver comentários "C1 FIX" no próprio arquivo) e não deve ganhar um segundo mecanismo de resolução de tenant concorrente sem desenho cuidadoso.

## R - Riscos

### Opção A — Reativar de verdade (instalar `TenantMainMiddleware`, dar vida a `PUBLIC_SCHEMA_URLCONF`)

Isso criaria uma "porta/entrada" real e separada para login — o mais próximo do pedido original ("duas entradas pra mesma casa, só outro cômodo").

**Risco real, não hipotético:** o app já tem um mecanismo de resolução de tenant funcionando e testado (`TenantBySessionMiddleware`, baseado em `session['active_box_id']`/`Membership`, **não** em domínio). Instalar `TenantMainMiddleware` no topo do `MIDDLEWARE` criaria um **segundo mecanismo independente**, baseado em domínio, decidindo `request.urlconf` **antes** do primeiro rodar. Os dois podem discordar: `TenantMainMiddleware` resolveria schema pelo domínio (via `control.models.Domain`) e setaria `request.urlconf`; `TenantBySessionMiddleware` continuaria resolvendo schema pela sessão do usuário e chamando `connection.set_tenant()`/`set_schema_to_public()` **sem nunca olhar pra `request.urlconf`**. Resultado possível: um request processado com o urlconf de um schema (ex.: public) mas com a conexão de banco apontando pra outro schema (o box do usuário) — o tipo de inconsistência que os comentários "C1 FIX" no próprio middleware já mostram que este projeto sofreu e corrigiu no passado.

Não é impossível de fazer direito — mas exige desenhar como os dois mecanismos convivem (provavelmente: `TenantMainMiddleware` só decide `urlconf`, nunca schema; `TenantBySessionMiddleware` continua sendo a única fonte de verdade pra schema). Isso é trabalho de desenho, não uma reativação mecânica.

### Opção B — Reaproveitar como contrato de teste (não reativa urlconf nenhum)

Transforma `urls_public.py` de "código que finge rotear" em "lista declarativa das rotas que precisam sobreviver sem tenant", validada por um teste automático:
1. todo path pattern em `urls_public.py` também resolve em `config/urls.py`.
2. todo path pattern em `urls_public.py` está coberto por `TenantBySessionMiddleware.PUBLIC_SCHEMA_PATHS` (prefixo bate).

**Risco:** baixo. Não toca em middleware de tenant, não muda comportamento de request nenhum — só adiciona um teste que impede a lista de `PUBLIC_SCHEMA_PATHS` divergir da lista de rotas públicas sem ninguém perceber (hoje nada garante isso; é mantido só por disciplina de quem edita os dois lugares).

### Opção C — Excluir

Remove `config/urls_public.py` e `PUBLIC_SCHEMA_URLCONF` inteiramente.

**Risco:** baixíssimo, dado o mapeamento 1:1 confirmado na Seção C. Perde-se, porém, o valor de "lista central do que precisa funcionar sem tenant" — essa informação passaria a existir só implicitamente, espalhada em `PUBLIC_SCHEMA_PATHS` + `config/urls.py`.

### Risco comum às 3 opções

Nenhuma delas deve, por si só, virar desculpa para reabrir "separar login numa porta/processo diferente" sem antes reler a Seção C: o ganho real de uma porta separada (documentado agora) é isolamento de infraestrutura (nginx/WAF), não isolamento de tenant — isso já é resolvido pelo path-based middleware.

## D - Direção

**Recomendação: Opção B agora, Opção A registrada como possibilidade futura (não descartada, só não executada sem desenho), Opção C como alternativa mais simples a B se o time preferir não manter o arquivo.**

Por quê:
- Opção B é a que fecha o buraco real (código morto que engana) com o menor risco possível — vira um teste de regressão, não uma reescrita de middleware.
- Opção A é a única que entrega literalmente "outra entrada" — mas o próprio pedido original que motivou essa investigação foi esclarecido pelo usuário como sendo sobre **não confundir os apps**, não sobre isolamento técnico de tenant. Isso já está satisfeito hoje: `/login/`, `/aluno/auth/`, `/checkout/`, `/onboarding/` já são um conjunto de rotas claramente distinto (a "entrada" de pré-autenticação), só que dentro do mesmo urlconf — o que já é suficiente pra "outro cômodo" no sentido organizacional. Se no futuro isso precisar virar isolamento de infraestrutura de verdade (rate-limit/WAF dedicado), a mitigação certa é a que já foi implementada nesta sessão em `infra/hostgator-vps/nginx/app.octoboxfit.com.br.conf` (limite de request no Nginx para essas mesmas rotas) — não reativar `TenantMainMiddleware`.
- Opção C fica registrada como alternativa válida: se o time achar que manter um arquivo + teste só pra documentar "rotas públicas" é peso desnecessário, excluir é seguro. A diferença pra B é filosófica (manter um contrato vivo vs. confiar só na disciplina humana), não de risco.

### Frase de arquitetura

`Tenant é resolvido por sessão (quem você é), não por domínio/porta (onde você bateu) — qualquer proposta de "porta separada" que não passar por essa frase primeiro está resolvendo o problema errado.`

## A - Ação

## Onda 1 - Parar a desinformação (feito nesta revisão)

### O que fazer
1. corrigir o docstring de `config/urls_public.py` pra declarar o estado real (morto, não usado), com link pra este plano.
2. registrar o achado em `CLAUDE.md` > Gotchas de runtime (local lido por qualquer agente antes de mexer no repo).

### Pronto quando
1. ninguém que abrir `urls_public.py` ou `CLAUDE.md` sai enganado sobre o que o arquivo faz.

## Onda 2 - Opção B: contrato de teste (recomendada, ainda não executada)

### O que fazer
1. escrever `tests/test_public_schema_routes_contract.py` (ou local equivalente) que:
   - itera os `urlpatterns` de `config.urls_public`.
   - para cada um, confirma que o mesmo path resolve em `config.urls` (via `django.urls.resolve`).
   - confirma que o path está coberto por `control.middleware.PUBLIC_SCHEMA_PATHS` (prefixo).
2. se o teste passar de primeira (deve passar, dado o mapeamento já confirmado), `urls_public.py` vira oficialmente "fixture declarativa" — atualizar o docstring uma segunda vez pra refletir esse novo papel (de "seria usado pelo django-tenants" para "lista de contrato, validada por teste").

### O que não entra
- nenhuma mudança em `MIDDLEWARE`, `TenantBySessionMiddleware` ou `PUBLIC_SCHEMA_URLCONF`.

### Pronto quando
1. o teste existe, passa, e falharia se alguém adicionar um path a `urls_public.py` sem o path equivalente existir em `config/urls.py` ou em `PUBLIC_SCHEMA_PATHS`.

## Onda 3 (alternativa a Onda 2, não as duas) - Opção C: excluir

Só executar esta onda **em vez da** Onda 2, se o time decidir que não vale manter o arquivo. Não fazer as duas.

### O que fazer
1. remover `config/urls_public.py`.
2. remover `PUBLIC_SCHEMA_URLCONF` de `config/settings/base.py`.
3. atualizar `CLAUDE.md` (a linha desta revisão) pra "arquivo removido em [data], ver git history se precisar".

### Pronto quando
1. `grep -r PUBLIC_SCHEMA_URLCONF` não acha nada fora do git log.

## Onda 4 (futuro, não agendada) - Opção A: reativar de verdade

Não entra em execução sem um desenho explícito de como `TenantMainMiddleware` (urlconf por domínio) e `TenantBySessionMiddleware` (schema por sessão) convivem sem os dois decidirem coisas diferentes pro mesmo request. Só considerar se aparecer um requisito real de isolamento por domínio (não só organização de rotas) que a Opção B/C não resolvam.

## Critérios de pronto globais

1. `config/urls_public.py` nunca mais afirma algo que o runtime não faz.
2. existe exatamente 1 mitigação executada (B ou C, não as duas) — se nenhuma foi executada ainda, este plano continua ABERTO, não abandonado.
3. `PUBLIC_SCHEMA_PATHS` continua sendo a única fonte de verdade pra "roda sem tenant" — nenhuma mitigação introduz um segundo mecanismo concorrente sem o desenho da Onda 4.
