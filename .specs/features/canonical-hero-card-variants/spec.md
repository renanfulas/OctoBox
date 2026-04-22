# Spec

## Objetivo

Criar uma arquitetura onde `hero`, `card` e `table-card` sejam componentes canonicos de verdade, com variantes oficiais e sem repaint local paralelo.

## Resultado esperado

- um ajuste no host ou numa variante oficial repercute nas superficies relacionadas sem mexer tela por tela
- paginas locais passam a compor o sistema em vez de reinventar o container visual
- `dashboard`, `financeiro`, `owner` e outras superficies migram para variantes previsiveis
- dark mode e light mode passam a seguir a mesma espinha dorsal
- fica mais facil evoluir sem gerar debito tecnico recorrente

## Pergunta central que esta spec responde

Como fazer o produto se comportar como um design system de verdade, onde a familia visual mora no componente e nao espalhada em overrides locais?
