# Evidence Map

## Runtime vivo observado

1. [index.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/dashboard/index.html)
2. [dashboard_reading_list.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/includes/ui/layout/dashboard_reading_list.html)
3. [page_reading_list.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/includes/ui/layout/page_reading_list.html)
4. [cards.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/design-system/components/cards.css)

## Trilha morta ou ambigua removida

1. [priority_strip.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/dashboard/blocks/priority_strip.html)
2. [dashboard_glance_card.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/includes/ui/dashboard/dashboard_glance_card.html)
3. [summary.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/design-system/components/dashboard/summary.css)
4. [glance_cards.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/design-system/components/dashboard/glance/glance_cards.css)
5. [glance_neon.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/design-system/components/dashboard/glance/glance_neon.css)

## Infra de assets

1. [static_assets.py](C:/Users/renan/OneDrive/Documents/OctoBOX/shared_support/static_assets.py)
2. [sync_runtime_assets.py](C:/Users/renan/OneDrive/Documents/OctoBOX/shared_support/management/commands/sync_runtime_assets.py)
3. [components.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/design-system/components.css)
4. [cards.css](C:/Users/renan/OneDrive/Documents/OctoBOX/staticfiles/css/design-system/components/cards.css)
5. [dashboard.css](C:/Users/renan/OneDrive/Documents/OctoBOX/staticfiles/css/design-system/dashboard.css)

## Espelho OctoBox

1. [presentation.py](C:/Users/renan/OneDrive/Documents/OctoBOX/OctoBox/dashboard/presentation.py) ainda carrega `priority_strip` e pertence ao legado divergente
2. [test_dashboard.py](C:/Users/renan/OneDrive/Documents/OctoBOX/OctoBox/boxcore/tests/test_dashboard.py) ainda testa a familia antiga do dashboard
3. [components.css](C:/Users/renan/OneDrive/Documents/OctoBOX/OctoBox/static/css/design-system/components.css) ainda importa `summary.css`
4. [priority_strip.html](C:/Users/renan/OneDrive/Documents/OctoBOX/OctoBox/templates/dashboard/blocks/priority_strip.html) e a trilha antiga devem ser tratados como legado, nao como runtime de referencia

## Pontos de override e risco

1. [neon.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/design-system/neon.css)
2. [metrics.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/design-system/components/dashboard/metrics.css)
3. [metric_card.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/includes/ui/shared/metric_card.html)
4. [test_dashboard.py](C:/Users/renan/OneDrive/Documents/OctoBOX/boxcore/tests/test_dashboard.py)
