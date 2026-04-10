<!--
ARQUIVO: mapa do contrato de cache local para busca de telas ricas.

POR QUE ELE EXISTE:
- evita que busca local volte a bater no backend a cada tecla.
- registra a regra de versionamento para que cache velho nao pareca dado vivo.
- transforma a estrategia de performance em contrato legivel, nao em truque escondido no JS.

O QUE ESTE ARQUIVO FAZ:
1. define como busca local deve carregar, guardar e invalidar indices.
2. explica a diferenca entre cache local valido e cache cosmetico inutil.
3. aponta onde o contrato nasce no backend e onde ele e consumido no frontend.

PONTOS CRITICOS:
- este contrato nao e para qualquer tela pequena; ele vale para superficies com busca rica e custo perceptivel de request.
- `sessionStorage` e preferido a cookie para esse caso porque nao polui todas as requests.
- `refresh_token` nao pode nascer de relogio puro; ele precisa nascer do estado real da base.
-->

# Mapa do contrato de cache local para busca

Este documento existe para responder:

1. quando a busca deve usar indice local
2. como esse indice fica guardado
3. quando ele deixa de ser confiavel
4. por que o sistema nao deve consultar o backend a cada letra

Em linguagem simples:

1. a primeira visita pega um caderno da turma
2. o navegador guarda esse caderno no armario
3. nas proximas buscas ele consulta o caderno local
4. so troca de caderno quando percebe que a turma mudou de verdade

## Regra geral

Para buscas ricas do front-end do OctoBox, a ordem preferida e:

1. backend monta um indice inicial
2. payload entrega `cache_key`, `refresh_token` e `index`
3. frontend guarda isso em `sessionStorage`
4. digitacao filtra localmente
5. cache e descartado quando o `refresh_token` nao bate mais

## Por que `sessionStorage` vence cookie aqui

Use `sessionStorage` por padrao para indice de busca.

Motivos:

1. cookie viaja em toda request HTTP
2. `sessionStorage` fica so no navegador
3. indice de busca e dado de apoio de UI, nao contrato que o servidor precise receber de volta

Metafora curta:

1. cookie e levar a mochila para toda corrida
2. `sessionStorage` e deixar a mochila no armario da academia

## Shape oficial do contrato

O backend deve entregar um bloco em `page.behavior` com esta forma:

1. `cache_key`
2. `refresh_token`
3. `index`

Exemplo conceitual:

```json
{
  "cache_key": "student_status=active",
  "refresh_token": "42:2026-04-09T10:15:00:2026-04-09T10:10:00",
  "index": []
}
```

## Regra de `cache_key`

`cache_key` representa o recorte da busca.

Ele deve mudar quando mudar a moldura do conjunto.

Exemplos:

1. filtro ativo vs inativo
2. janela de tempo
3. status comercial
4. status financeiro

Regra pratica:

1. se dois recortes podem produzir indices diferentes, eles nao devem compartilhar `cache_key`

## Regra de `refresh_token`

`refresh_token` representa a versao do conjunto.

Ele nao deve nascer de `timezone.now()` ou outro relogio puro.

Ele deve nascer de sinais reais de mutacao, como:

1. contagem total do conjunto
2. maior `updated_at` do model principal
3. maior `updated_at` das relacoes que alteram leitura da tabela

### Bons exemplos

#### Alunos

O token deve considerar:

1. aluno
2. matricula
3. pagamento
4. presenca

Arquivos vivos:

1. [catalog/student_queries.py](C:/Users/renan/OneDrive/Documents/OctoBOX/catalog/student_queries.py)
2. [catalog/views/student_views.py](C:/Users/renan/OneDrive/Documents/OctoBOX/catalog/views/student_views.py)
3. [student-directory.js](C:/Users/renan/OneDrive/Documents/OctoBOX/static/js/pages/students/student-directory.js)

#### Entradas

O token atual considera:

1. total da fila filtrada
2. maior `updated_at` do conjunto de `StudentIntake`

Arquivos vivos:

1. [onboarding/queries.py](C:/Users/renan/OneDrive/Documents/OctoBOX/onboarding/queries.py)
2. [onboarding/views.py](C:/Users/renan/OneDrive/Documents/OctoBOX/onboarding/views.py)
3. [intake-center.js](C:/Users/renan/OneDrive/Documents/OctoBOX/static/js/pages/onboarding/intake-center.js)

## Regra de invalidaçao

O frontend deve invalidar a cache quando:

1. `cache_key` mudou
2. `refresh_token` do payload nao bate com o salvo
3. uma mutacao local relevante marca o indice como velho

### Invalidaçao por mutacao local

Se a propria tela executa mutacoes que alteram leitura da lista, o JS pode marcar o indice como stale.

Isso vale quando:

1. salvar perfil muda nome ou status
2. acao financeira muda leitura da fila
3. acao de matricula muda o estado operacional da linha

Mas a regra de ouro continua:

1. o carimbo final de verdade e o `refresh_token` do backend

## O que o frontend deve fazer

Quando a tela carrega:

1. ler o payload
2. procurar cache local com a mesma `cache_key`
3. comparar `refresh_token`
4. se bater, reutilizar o indice
5. se nao bater, persistir o indice novo

Quando o usuario digita:

1. filtrar localmente
2. evitar request por tecla
3. manter ordenacao local funcionando sobre o conjunto filtrado

## O que o backend nao deve fazer

Evite estes anti-padroes:

1. gerar `refresh_token` com `timezone.now()` em toda renderizacao
2. montar cache local em cookie por conveniencia
3. mandar indice gigante sem `cache_key`
4. mandar indice sem criterio claro de invalidacao

Metafora curta:

1. um token de relogio e um alarme que toca a cada minuto
2. um token de estado e um sensor que dispara so quando alguem abriu a porta

## Quando usar este contrato

Use quando a tela tiver:

1. lista rica
2. busca por digitacao
3. recorte grande o suficiente para request por tecla incomodar
4. necessidade de resposta perceptivelmente instantanea

Nao use por reflexo quando:

1. a lista e pequena demais
2. a busca e rara
3. o custo de montar indice supera o ganho de UX

## Checklist curto

- [ ] a tela realmente precisa de busca local?
- [ ] existe `cache_key` separado por recorte?
- [ ] o `refresh_token` nasce de estado real?
- [ ] o frontend compara o token salvo com o token atual?
- [ ] a digitacao evita request por tecla?
- [ ] a ordenacao continua funcionando sobre o resultado filtrado?

## Mapas irmaos

1. [front-end-forensics-map.md](C:/Users/renan/OneDrive/Documents/OctoBOX/docs/map/front-end-forensics-map.md)
2. [front-end-contract-forensics-map.md](C:/Users/renan/OneDrive/Documents/OctoBOX/docs/map/front-end-contract-forensics-map.md)
3. [front-end-error-patterns-map.md](C:/Users/renan/OneDrive/Documents/OctoBOX/docs/map/front-end-error-patterns-map.md)
