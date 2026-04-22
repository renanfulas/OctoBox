# Dashboard Runtime And Asset Drift Cleanup

## Norte

Eliminar a confusao estrutural atual entre:

1. a abertura viva do dashboard
2. a familia morta de `priority_strip` e `dashboard_glance_card`
3. a dupla fonte de verdade entre `static/` e `staticfiles/`
4. a variante de dashboard embutida no componente generico `page_reading_list.html`

## Tese

O dashboard precisa ter:

1. uma unica fachada viva
2. uma unica trilha de assets confiavel
3. uma unica narrativa de manutencao

Sem override invisivel, sem regra fantasma e sem espelho mentiroso.
