<!--
ARQUIVO: blueprint tecnico da onda 1 de split em apps reais.

TIPO DE DOCUMENTO:
- blueprint de onda arquitetural

AUTORIDADE:
- media

DOCUMENTO PAI:
- [app-split-plan.md](app-split-plan.md)

QUANDO USAR:
- quando a duvida for o que entra na primeira onda real de separacao e como executar sem romper o runtime

POR QUE ELE EXISTE:
- Traduz a primeira onda de migracao em uma sequencia objetiva de arquivos, impactos e validacoes.
- Evita improviso quando comecarmos a transformar api, jobs e integrations em apps Django reais.

O QUE ESTE ARQUIVO FAZ:
1. Lista arquivo por arquivo o que sai de boxcore.
2. Define a ordem de implementacao por passos pequenos.
3. Mapeia impacto em settings, urls, imports e testes.

PONTOS CRITICOS:
- Esta onda deve preservar rotas, nomes de teste, imports e comportamento externo.
- O objetivo aqui e mover a fronteira, nao alterar regra de negocio.
-->

# Blueprint tecnico da onda 1

## Objetivo

Transformar tres fronteiras ja existentes em apps Django reais, com risco baixo e quase sem tocar no core historico:

1. `api`
2. `jobs`
3. `integrations`

Nesta onda, a regra e simples:

1. mover a organizacao do codigo
2. manter comportamento identico
3. preservar imports antigos temporariamente quando isso reduzir risco
4. nao mexer em models historicos nem em app label de migrations

## Resultado esperado

Ao final da onda 1, o projeto deve ficar assim:

```text
api/
  __init__.py
  apps.py
  urls.py
  views.py
  v1/
    __init__.py
    urls.py
    views.py

jobs/
  __init__.py
  apps.py
  base.py

integrations/
  __init__.py
  apps.py
  whatsapp/
    __init__.py
    contracts.py
    identity.py
    payloads.py
    services.py
```

E o `INSTALLED_APPS` deve passar a listar esses apps explicitamente.

## Escopo exato da onda 1

### 1. App real `api`

#### Arquivos de origem atuais

1. `boxcore/api/__init__.py`
2. `boxcore/api/urls.py`
3. `boxcore/api/views.py`
4. `boxcore/api/v1/__init__.py`
5. `boxcore/api/v1/urls.py`
6. `boxcore/api/v1/views.py`

#### Destino alvo

1. `api/__init__.py`
2. `api/apps.py`
3. `api/urls.py`
4. `api/views.py`
5. `api/v1/__init__.py`
6. `api/v1/urls.py`
7. `api/v1/views.py`

#### Arquivos que precisam ser ajustados por impacto

1. `config/settings/base.py`
2. `boxcore/urls.py`
3. `config/urls.py`, se em algum momento a rota de API sair do agregador do boxcore
4. `boxcore/tests/test_api.py`
5. `../reference/reading-guide.md`
6. `README.md`

#### Ajuste tecnico esperado

1. criar `ApiConfig`
2. trocar `include('boxcore.api.urls')` por `include('api.urls')`
3. manter opcionalmente `boxcore/api/*` como casca temporaria de compatibilidade na primeira iteracao

#### Risco

Baixo.

Nao depende de model historico, sinal complexo ou admin.

### 2. App real `jobs`

#### Arquivos de origem atuais

1. `boxcore/jobs/__init__.py`
2. `boxcore/jobs/base.py`

#### Destino alvo

1. `jobs/__init__.py`
2. `jobs/apps.py`
3. `jobs/base.py`

#### Arquivos que precisam ser ajustados por impacto

1. `config/settings/base.py`
2. `../reference/reading-guide.md`
3. `README.md`
4. qualquer import futuro que aponte para `boxcore.jobs.base`

#### Ajuste tecnico esperado

1. criar `JobsConfig`
2. trocar imports futuros para `jobs.base`
3. manter `boxcore/jobs/base.py` como alias temporario se quisermos custo minimo de transicao

#### Risco

Muito baixo.

Hoje e uma fronteira pequena e sem dependencia de banco.

### 3. App real `integrations`

#### Arquivos de origem atuais

1. `boxcore/integrations/__init__.py`
2. `boxcore/integrations/whatsapp/__init__.py`
3. `boxcore/integrations/whatsapp/contracts.py`
4. `boxcore/integrations/whatsapp/identity.py`
5. `boxcore/integrations/whatsapp/payloads.py`
6. `boxcore/integrations/whatsapp/services.py`

#### Destino alvo

1. `integrations/__init__.py`
2. `integrations/apps.py`
3. `integrations/whatsapp/__init__.py`
4. `integrations/whatsapp/contracts.py`
5. `integrations/whatsapp/identity.py`
6. `integrations/whatsapp/payloads.py`
7. `integrations/whatsapp/services.py`

#### Arquivos que precisam ser ajustados por impacto

1. `config/settings/base.py`
2. `boxcore/tests/test_integrations.py`
3. `boxcore/catalog/services/communications.py`
4. `../reference/reading-guide.md`
5. `README.md`

#### Ajuste tecnico esperado

1. criar `IntegrationsConfig`
2. trocar imports de `boxcore.integrations.whatsapp...` para `integrations.whatsapp...`
3. manter casca temporaria em `boxcore/integrations/` na primeira etapa para reduzir risco de import espalhado

#### Risco

Baixo para medio.

O codigo da integracao conversa com models e services existentes, mas nao carrega migrations proprias nem admin ainda.

## Arquivos que nao devem mudar nesta onda

Para manter custo controlado, estes pontos devem ficar como estao:

1. `boxcore/models/*.py`
2. `boxcore/migrations/*.py`
3. `boxcore/models/__init__.py`
4. `boxcore/apps.py`
5. `boxcore/admin/*.py`
6. app labels historicos do banco

## Ordem de implementacao recomendada

### Passo 1: criar apps reais vazios

Criar pastas e `AppConfig` para:

1. `api`
2. `jobs`
3. `integrations`

Sem mover nada ainda.

Objetivo:

1. registrar os novos apps no projeto
2. validar que o Django sobe com eles instalados

### Passo 2: mover `jobs`

Motivo:

1. e o menor bloco
2. valida o padrao de split com quase zero risco

Saida esperada:

1. `jobs/base.py` passa a ser o modulo real
2. `boxcore/jobs/base.py` pode virar alias temporario

### Passo 3: mover `api`

Motivo:

1. e uma fronteira publica e pequena
2. testa bem a mudanca de `urls` e `INSTALLED_APPS`

Saida esperada:

1. `api/urls.py` e `api/views.py` passam a ser os modulos reais
2. `boxcore/urls.py` passa a incluir `api.urls`
3. os testes de API continuam verdes sem mudar contrato externo

### Passo 4: mover `integrations`

Motivo:

1. fecha a onda 1 com a fronteira de provider e webhook pronta para crescer

Saida esperada:

1. `integrations/whatsapp/*` viram os modulos reais
2. services internos passam a importar do novo namespace
3. testes de integracao continuam verdes

### Passo 5: podar cascas antigas com calma

Depois da onda estabilizada:

1. manter alias em `boxcore/*` por um ciclo
2. procurar imports remanescentes
3. so depois reduzir ou matar as cascas antigas

## Tabela arquivo por arquivo

| Origem atual | Destino alvo | Tipo de acao | Observacao |
|---|---|---|---|
| `boxcore/api/__init__.py` | `api/__init__.py` | mover | baixo risco |
| `boxcore/api/urls.py` | `api/urls.py` | mover | ajustar include principal |
| `boxcore/api/views.py` | `api/views.py` | mover | contrato deve permanecer identico |
| `boxcore/api/v1/__init__.py` | `api/v1/__init__.py` | mover | baixo risco |
| `boxcore/api/v1/urls.py` | `api/v1/urls.py` | mover | nomes de rota devem permanecer |
| `boxcore/api/v1/views.py` | `api/v1/views.py` | mover | baixo risco |
| `boxcore/jobs/__init__.py` | `jobs/__init__.py` | mover | baixo risco |
| `boxcore/jobs/base.py` | `jobs/base.py` | mover | bom primeiro corte |
| `boxcore/integrations/__init__.py` | `integrations/__init__.py` | mover | baixo risco |
| `boxcore/integrations/whatsapp/__init__.py` | `integrations/whatsapp/__init__.py` | mover | baixo risco |
| `boxcore/integrations/whatsapp/contracts.py` | `integrations/whatsapp/contracts.py` | mover | sem mudar API interna |
| `boxcore/integrations/whatsapp/identity.py` | `integrations/whatsapp/identity.py` | mover | revisar imports de model |
| `boxcore/integrations/whatsapp/payloads.py` | `integrations/whatsapp/payloads.py` | mover | baixo risco |
| `boxcore/integrations/whatsapp/services.py` | `integrations/whatsapp/services.py` | mover | revisar imports e testes |

## Tabela de arquivos afetados indiretamente

| Arquivo | Motivo |
|---|---|
| `config/settings/base.py` | instalar novos apps reais |
| `boxcore/urls.py` | incluir `api.urls` novo |
| `boxcore/catalog/services/communications.py` | import de integracao muda |
| `boxcore/tests/test_api.py` | import path pode mudar |
| `boxcore/tests/test_integrations.py` | import path pode mudar |
| `README.md` | refletir namespace final |
| `../reference/reading-guide.md` | refletir namespace final |

## Testes minimos da onda 1

Ao final da implementacao, a validacao minima deve ser:

1. `manage.py check`
2. `boxcore.tests.test_api`
3. `boxcore.tests.test_integrations`
4. `boxcore.tests.test_catalog_services`, porque a comunicacao operacional toca integracao

## Definicao de pronto da onda 1

Podemos dizer que a onda 1 acabou quando:

1. `api`, `jobs` e `integrations` existem como apps Django reais com `AppConfig`
2. `INSTALLED_APPS` aponta para eles
3. as rotas e contratos externos continuam identicos
4. os testes verdes confirmam que nada funcional mudou
5. o `boxcore` deixa de ser dono conceitual dessas fronteiras

## Melhor proxima acao depois deste blueprint

Quando decidirmos implementar de verdade, a ordem mais inteligente e:

1. criar `jobs` real
2. criar `api` real
3. criar `integrations` real
4. rodar validacao
5. so depois planejar a onda 2 com `access` e `auditing`