<!--
ARQUIVO: mapa curto de prontidao para cache e render parcial.

POR QUE ELE EXISTE:
- deixa claro quais blocos do shell e das paginas ja estao prontos para virar fronteiras de cache.
- reduz improviso quando formos evoluir de SSR integral para shell persistente e fragment cache.
-->

# Mapa curto de prontidao para cache

## Ordem de leitura

Antes de mexer com cache ou render parcial, revise nesta ordem:

1. [../../shared_support/page_payloads.py](../../shared_support/page_payloads.py)
2. [../../shared_support/shell_payloads.py](../../shared_support/shell_payloads.py)
3. [../../access/context_processors.py](../../access/context_processors.py)
4. [../../templates/layouts/base.html](../../templates/layouts/base.html)
5. [front-end-ownership-map.md](front-end-ownership-map.md)

## Fonte canonica atual

### Page payload

Contrato oficial:

1. `build_page_payload(...)`
2. `build_page_context(...)`
3. `build_page_hero(...)`

Responsabilidade:

1. contexto semantico da tela
2. dados da tela
3. capacidades
4. assets
5. comportamento

### Shell chrome

Contrato oficial:

1. `build_shell_chrome_payload(...)`
2. `build_shell_sidebar_payload(...)`
3. `build_shell_search_payload(...)`
4. `build_shell_profile_payload(...)`

Responsabilidade:

1. sidebar
2. topbar
3. contexto estrutural do shell
4. contadores globais

## Mapa do que tende a ser estatico ou dinamico

### Estatico forte

Pode ser cacheado com agressividade:

1. marca da sidebar
2. estrutura da topbar
3. theme toggle
4. assets CSS e JS versionados

### Semi-estatico por papel

Pode ser fragmentado por `role_slug`:

1. navegacao da sidebar
2. quick links da topbar
3. scope e section title do shell

### Semi-estatico por usuario

Pode ser fragmentado por `user_id`:

1. identidade da sidebar
2. profile da topbar

### Dinamico volatil

Nao deve invalidar a shell inteira:

1. `shell_counts`
2. alert chips da topbar
3. listas e metricas da pagina
4. tabs interativas

## Boundaries recomendadas para cache futuro

### Boundary 1: shell

Inclui:

1. `sidebar`
2. `topbar`
3. `page-body`

Regra:

1. a shell deve conseguir permanecer montada enquanto o `page-body` troca

### Boundary 2: hero canonico

Inclui:

1. payload do hero
2. host `page_hero.html`
3. contrato visual em `components/hero.css` e `operations/refinements/hero.css`

Regra:

1. o hero pode ser tratado como fragmento compartilhado se o payload continuar semantico

### Boundary 3: paineis vivos

Inclui:

1. contadores
2. chips de alerta
3. tabelas
4. filas

Regra:

1. atualizar separado do shell quando precisarem frescor maior

## Anti-padroes para evitar

1. cachear HTML inteiro quando so um contador muda
2. colocar regra visual local dentro do payload
3. criar nova variavel global do shell para um ajuste de uma pagina
4. fazer topbar ou sidebar depender de dados especificos demais de uma tela

## Sinal verde para a proxima fase

Podemos entrar em fragment cache ou shell persistente quando:

1. `hero`, `topbar` e `sidebar` estiverem sem overrides estruturais relevantes
2. `shell_chrome` estiver sendo consumido como contrato principal
3. os payloads das paginas principais estiverem com `context`, `data`, `actions`, `behavior`, `capabilities` e `assets` estaveis
