# Context

## Problema central

Hoje o dashboard sofre com um tripé de confusao:

1. a tela viva usa `page_reading_list.html`
2. o projeto ainda carrega e mantem `priority_strip` + `dashboard_glance_card`
3. o runtime de CSS pode servir arquivos de `staticfiles/` fora de sincronia com `static/`

## Sinais observados

1. mudancas corretas em `static/` nao aparecem ate sincronizar `staticfiles/`
2. correcoes feitas em `dashboard_glance_card` nao alteram o card visivel
3. `page_reading_list.html` ganhou regra especifica de dashboard e ficou fragil
4. `neon.css` usa um campo de forca com `!important` na lateral do dashboard
5. testes ainda contam uma historia parcialmente antiga

## Analogia

E como ter:

1. uma porta nova funcionando
2. a porta antiga ainda recebendo manutencao
3. dois mapas da mesma casa

Assim a equipe abre a caixa certa por sorte, nao por contrato.
