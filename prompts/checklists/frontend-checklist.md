<!--
ARQUIVO: checklist de front-end do OctoBOX.

POR QUE ELE EXISTE:
- garante que UI, UX, assets e comportamento evoluam juntos.

O QUE ESTE ARQUIVO FAZ:
1. valida estrutura visual, ownership de assets e comportamento.
2. ajuda a preparar a base para escalar UI ou UX sem retrabalho.

PONTOS CRITICOS:
- front-end pode parecer pronto e ainda estar estruturalmente fragil.
-->

# Frontend Checklist

Marque cada item antes de fechar uma tarefa de front-end:

- a acao principal da tela ficou obvia?
- a hierarquia visual ficou mais clara?
- shell, shared e domain foram separados corretamente?
- o CSS tem ownership claro?
- o JS deixou de controlar aparencia via inline style quando isso era problema?
- `onclick`, `window.*` ou handlers inline foram removidos das areas criticas?
- estados de erro, vazio, loading ou sucesso foram considerados quando relevantes?
- a pagina continua boa em mobile e desktop?
- os assets carregados pertencem a esta pagina ou shell de verdade?
- a performance percebida melhorou ou pelo menos nao piorou?

Se a tela ficou mais bonita mas mais acoplada, a conta chega depois.
