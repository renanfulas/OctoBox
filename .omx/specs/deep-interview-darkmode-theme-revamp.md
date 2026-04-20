# Deep Interview Spec — darkmode-theme-revamp

## Metadata
- Profile: standard
- Rounds: 5
- Final ambiguity: 0.07
- Threshold: 0.20
- Context type: brownfield
- Context snapshot: `.omx/context/darkmode-theme-revamp-20260420T094341Z.md`
- Interview transcript: latest `.omx/interviews/darkmode-theme-revamp-*.md`

## Clarity breakdown
| Dimension | Score |
| --- | ---: |
| Intent clarity | 0.88 |
| Outcome clarity | 0.92 |
| Scope clarity | 0.99 |
| Constraint clarity | 0.99 |
| Success criteria clarity | 0.92 |
| Context clarity | 0.90 |

## Intent (why)
Repaginar o dark mode do OctoBox para transmitir modernidade, ação, agilidade e magnetismo, sem cair em estética gamer, carnaval visual ou perda de conforto operacional em uso prolongado.

## Desired outcome
Um dark mode global, ancorado no tema oficial do OctoBox, mais magnético e contemporâneo, com neons usados de forma disciplinada e estratégica, preservando a serenidade operacional do conteúdo e a boa experiência do light mode.

## In-scope
- Revisão global das **cores/tokens do dark mode**.
- Ajuste da paleta escura base para suportar sensação de modernidade, ação, agilidade e magnetismo.
- Redistribuição semântica das cores de ênfase no dark mode para destacar:
  1. CTA primária
  2. foco ativo
  3. métricas críticas

## Out-of-scope / Non-goals
- Não mexer no light mode.
- Não mexer em layout, spacing, estrutura, componentes, comportamento, animações, densidade ou hierarquia física.
- Não criar tema paralelo local por tela.
- Não espalhar neon fora dos 3 pontos prioritários.

## Decision Boundaries (what OMX may decide without confirmation)
OMX pode decidir sem pedir confirmação adicional:
- a combinação exata das cores base do dark mode;
- a calibragem tonal entre fundo, superfície, borda e texto no dark;
- qual dos acentos oficiais do tema melhor serve cada um dos 3 pontos prioritários;
- os ajustes de contraste necessários para manter legibilidade.

OMX **não** pode decidir sem confirmação adicional:
- alterar light mode;
- mexer em layout/estrutura/comportamento;
- introduzir novos pontos de neon forte além de CTA primária, foco ativo e métricas críticas;
- aceitar uma solução que aumente fadiga visual ou pareça gamer/carnaval.

## Constraints
- A mudança deve ocorrer **somente nas cores do dark mode**.
- A base deve respeitar `docs/architecture/themeOctoBox.md` e o fluxo `token -> host -> variante -> CSS local`.
- A autoridade principal deve nascer em `static/css/design-system/tokens.css`.
- Magnetismo vence apenas nas CTAs e métricas críticas; no resto, legibilidade vence.
- Impacto de performance aceitável: até ~10%; acima disso reprova.

## Testable acceptance criteria
1. O light mode permanece visualmente intocado.
2. Nenhum layout, spacing, componente ou comportamento muda; só o dark mode muda de cor.
3. O dark mode transmite mais modernidade, ação, agilidade e magnetismo sem parecer gamer.
4. O neon forte fica restrito a:
   - CTA primária
   - foco ativo
   - métricas críticas
5. O restante da interface permanece com legibilidade dominante e leitura serena para operação longa.
6. Após ~10 minutos de uso, a interface não deve parecer cansativa.
7. O impacto de performance percebida/medida não deve ultrapassar ~10%.
8. A solução deve nascer de tokens globais do dark mode, evitando tema paralelo local.

## Assumptions exposed + resolutions
- **Assumption:** o usuário queria uma repaginação ampla, possivelmente estrutural.
  - **Resolution:** falso; ele quer mudar exclusivamente as cores do dark mode.
- **Assumption:** magnetismo deveria dominar toda a interface.
  - **Resolution:** falso; ele deve dominar apenas CTA primária e métricas críticas, enquanto legibilidade domina o restante.
- **Assumption:** a mudança poderia ser por escopo premium local.
  - **Resolution:** falso; a decisão foi por mudança global do design system.

## Pressure-pass findings
A ambição inicial de “magnetismo” foi pressionada contra o risco de fadiga e perda de clareza. O resultado refinado foi:
- magnetismo forte apenas nos pontos de ação/prioridade máxima;
- legibilidade e serenidade operacional no restante;
- reprovação imediata se a interface cansar em uso contínuo ou comprometer performance além do limite aceito.

## Brownfield evidence vs inference
### Evidence
- `docs/architecture/themeOctoBox.md` define Luxo Futurista 2050, neon controlado e proíbe estética gamer/carnaval.
- `docs/map/design-system-contract.md` define `static/css/design-system/tokens.css` como autoridade global de tokens.
- `docs/experience/css-guide.md` exige evitar tema paralelo e seguir `token -> host -> variante -> CSS local`.
- `static/css/design-system/tokens.css` contém os tokens atuais do dark mode global.

### Inference
- A forma mais segura de executar a frente é reorquestrar os tokens do dark mode global primeiro, antes de qualquer ajuste fino em hosts compartilhados.

## Technical context findings
- Principal touchpoint: `static/css/design-system/tokens.css`
- Shared consumers likely affected: 
  - `static/css/design-system/components/cards.css`
  - `static/css/design-system/components/hero.css`
  - `static/css/design-system/components/actions.css`
- Risco principal de débito técnico: tentar simular o novo tema com overrides locais em vez de recalibrar os tokens globais do dark.

## Recommended handoff
### Recommended: `$ralplan`
Use este spec como fonte de verdade para planejar a execução com segurança arquitetural antes de implementar.

Suggested invocation:
`$plan --consensus --direct .omx/specs/deep-interview-darkmode-theme-revamp.md`
