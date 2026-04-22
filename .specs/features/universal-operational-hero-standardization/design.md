# Design

## Fonte da verdade

O owner sera tratado como molde visual do hero canonico.

Arquivos centrais esperados:

- `templates/includes/ui/layout/page_hero.html`
- `static/css/design-system/operations/refinements/hero.css`
- `templates/operations/owner.html`

## Contrato pretendido

### Bloco principal

- `operation-hero`
- `operation-hero-main`
- `operation-hero-copy`
- `operation-hero-eyebrow`
- `operation-hero-title`
- `operation-hero-body`

### Trilho de acoes

- `operation-hero-action-rail`
- acao primaria
- acoes secundarias

## Regras

1. texto e acoes nao disputam o mesmo eixo visual
2. o miolo do hero nao vira "texto com botoes enfiados"
3. o action rail e previsivel entre telas
4. cada pagina pode variar conteudo, nao a espinha dorsal
5. responsividade deve manter a mesma logica, nao inventar layouts paralelos

## Ondas de migracao sugeridas

1. manager
2. recepcao
3. coach
4. financeiro
5. ficha do aluno
