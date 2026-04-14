<!--
ARQUIVO: mapa de fronteira entre runtime ativo e arvore espelho do front-end.

POR QUE ELE EXISTE:
- evita tratar a pasta `OctoBox/` como se fosse a arvore principal de runtime.
- reduz falso positivo em auditoria de CSS, templates, inline style e legado.
- registra a prova tecnica de onde o Django realmente carrega templates e static files.

O QUE ESTE ARQUIVO FAZ:
1. define a fronteira entre runtime ativo, build output e arvore espelho.
2. lista as evidencias que sustentam essa fronteira.
3. orienta como investigar sem confundir reflexo com producao viva.

PONTOS CRITICOS:
- este mapa descreve o runtime atual da raiz do projeto.
- se settings mudarem para incluir `OctoBox/templates` ou `OctoBox/static`, este documento precisa ser revisado.
- `staticfiles/` continua sendo output de coleta, nao fonte de autoria.
-->

# Mapa de fronteira do runtime front-end

## Veredito rapido

No runtime atual deste projeto:

1. `templates/` e a arvore principal de templates
2. `static/` e a arvore principal de autoria de assets
3. `staticfiles/` e output coletado
4. `OctoBox/` deve ser tratado como arvore espelho, legado de referencia e deposito de artefatos antigos, nao como fonte primaria de runtime

Em linguagem simples:

1. `templates/` e a cozinha onde a comida e feita
2. `static/` e a bancada onde os ingredientes ficam
3. `staticfiles/` e o prato montado para servir
4. `OctoBox/` e a foto antiga da cozinha, com alguns utensilios ainda guardados

## Evidencias do veredito

### Templates ativos

Em [../../config/settings/base.py](../../config/settings/base.py), a configuracao oficial do Django aponta para:

1. `TEMPLATES[0]['DIRS'] = [BASE_DIR / 'templates']`
2. `APP_DIRS = True`

Nao ha inclusao de:

1. `BASE_DIR / 'OctoBox/templates'`
2. qualquer alias para `OctoBox/templates`

### Static files ativos

Ainda em [../../config/settings/base.py](../../config/settings/base.py), o runtime oficial aponta para:

1. `STATIC_ROOT = BASE_DIR / 'staticfiles'`
2. `STATICFILES_DIRS = [BASE_DIR / 'static']`

Nao ha inclusao de:

1. `BASE_DIR / 'OctoBox/static'`
2. qualquer alias para `OctoBox/static`

### Ponto de entrada do projeto

O [../../manage.py](../../manage.py) da raiz usa `config.settings` como entrada principal do projeto atual.

Isso reforca que a raiz do workspace e a aplicacao ativa.

### Cheiro estrutural da arvore `OctoBox/`

A pasta [../../OctoBox](../../OctoBox) contem varios sinais de espelho e historico:

1. outro `manage.py`
2. outro `README.md`
3. `login_response.html`, `dashboard_status.txt`, `debug_login_page.html` e outros artefatos de captura
4. duplicatas de `templates/` e `static/`

Esse conjunto se comporta mais como snapshot paralelo de trabalho antigo do que como arvore ativa do runtime atual.

### Evidencia documental

Ha specs que ja tratam explicitamente a trilha `OctoBox/` como legado de referencia.

Exemplo:

1. [../../.specs/features/dashboard-runtime-and-asset-drift-cleanup/evidence-map.md](../../.specs/features/dashboard-runtime-and-asset-drift-cleanup/evidence-map.md) registra que trilhas em `OctoBox/` devem ser tratadas como legado, nao como runtime de referencia

## Como investigar sem errar a arvore

### Use como fonte primaria

1. [../../templates](../../templates)
2. [../../static](../../static)
3. presenters, views e builders que apontam para esses caminhos

### Use como fonte secundaria

1. [../../OctoBox/templates](../../OctoBox/templates)
2. [../../OctoBox/static](../../OctoBox/static)

Somente para:

1. comparar drift historico
2. entender origem de naming legado
3. localizar artefato espelho que ainda polui scanner

### Nao use como prova final de runtime

1. `OctoBox/templates`
2. `OctoBox/static`
3. `staticfiles/`

Essas trilhas podem explicar por que um nome antigo apareceu no scanner, mas nao bastam para justificar uma correcao no runtime principal.

## Regra operacional para auditoria

Quando um achado aparecer so em `OctoBox/`:

1. classificar primeiro como `mirror-tree-only`
2. checar se existe correspondencia em `templates/` ou `static/`
3. so promover para problema ativo se houver prova na arvore principal ou no carregamento real

Quando um achado aparecer em `staticfiles/`:

1. tratar como output coletado
2. procurar o arquivo autor em `static/`
3. nunca corrigir o output antes da fonte

## Aplicacao desta regra na Onda 2

Com a fronteira atual, o veredito da Onda 2 fica assim:

1. o `style=""` fixo em [../../templates/catalog/student-source-capture.html](../../templates/catalog/student-source-capture.html) era runtime ativo e foi corrigido
2. os `style="--bar-width"` e `style="--bar-height"` encontrados apenas em `OctoBox/templates/...` nao sao prova suficiente de problema no runtime principal
3. o `<style>` localizado em `OctoBox/templates/access/login.html` entra como drift de arvore espelho, nao como bug ativo da tela principal de login

## Regra de decisao

Se um bug, seletor ou inline style existir apenas em `OctoBox/`, a pergunta correta nao e:

1. "como eu removo isso agora?"

A pergunta correta e:

1. "isso ainda sobe no runtime principal ou e so uma fotografia antiga?"
