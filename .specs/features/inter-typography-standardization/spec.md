# Inter Typography Standardization Specification

## Problem Statement

O OctoBOX hoje já nasce com `Inter` como fonte principal no design system:

- `--font-body` aponta para `Inter`
- `--font-display` também aponta para `Inter`
- o `base.html` carrega `Inter` globalmente

Mas ainda existem exceções visuais espalhadas em superfícies específicas, principalmente:

- `login.css` usando `Aptos` e `Rockwell`
- trechos isolados com `monospace`
- fontes técnicas de emoji/símbolo

O problema não é só “ter outra fonte”.

O problema real é não existir um contrato explícito dizendo:

1. onde `Inter` é obrigatória
2. onde a exceção é saudável
3. onde a exceção virou drift visual

Sem isso, a tipografia do produto corre o risco de ficar como uma banda em que quase todo mundo toca a mesma música, mas um instrumento ainda está em outro tom.

Em metáfora simples:

`Inter` já é a voz da casa.
Esta frente existe para garantir que todos os cômodos falem com a mesma voz, e que qualquer exceção seja intencional, não acidente.

## Goals

- [ ] Declarar `Inter` como a tipografia canônica do produto para superfícies de produto
- [ ] Padronizar cards, páginas e títulos principais para o contrato tipográfico em `Inter`
- [ ] Separar exceções saudáveis de exceções que precisam migrar
- [ ] Reduzir drift visual tipográfico entre páginas importantes
- [ ] Evitar novas sobrescritas locais sem justificativa

## Out of Scope

| Feature | Reason |
| --- | --- |
| Redesenho completo de identidade visual | A frente é de padronização tipográfica, não de rebranding |
| Reescrita de todos os componentes antigos no mesmo passo | A migração deve ser disciplinada por payoff |
| Trocar `monospace` em contextos técnicos | Código, IDs, logs e números técnicos podem precisar de fonte monoespaçada |
| Mudar o comportamento do login além da tipografia | O alvo é alinhamento visual tipográfico |
| Ajustes de copywriting, conteúdo ou layout | Esta frente trata voz tipográfica, não conteúdo ou estrutura |

---

## User Stories

### P1: Inter as Canonical Product Voice

**User Story**: Como time de produto, queremos que `Inter` seja a fonte canônica das superfícies principais para que o sistema pareça um produto único e intencional.

**Acceptance Criteria**:

1. WHEN uma página ou card de produto usar tipografia base ou display THEN o sistema SHALL consumir `Inter` via tokens canônicos
2. WHEN uma superfície importante estiver fora do contrato THEN ela SHALL ser classificada como migrar, manter ou justificar
3. WHEN uma nova página for refinada THEN ela SHALL herdar a tipografia do sistema em vez de criar uma nova família local

---

### P1: Product Surfaces Stop Speaking Different Dialects

**User Story**: Como operador, quero que login, cards, páginas e painéis importantes pareçam parte do mesmo produto para que a experiência pareça coesa e profissional.

**Acceptance Criteria**:

1. WHEN o usuário navegar por superfícies principais THEN a leitura tipográfica SHALL parecer contínua
2. WHEN títulos, subtítulos e corpo de texto aparecerem THEN a hierarquia SHALL usar a mesma família tipográfica base
3. WHEN existir uma exceção visual deliberada THEN ela SHALL ser rara e claramente justificável

---

### P2: Exception Matrix for Typography

**User Story**: Como mantenedor, quero uma matriz clara de exceções para saber onde `Inter` é obrigatória e onde outra família ainda pode existir sem virar dívida silenciosa.

**Acceptance Criteria**:

1. WHEN uma exceção tipográfica for encontrada THEN ela SHALL ser rotulada como `saudável`, `temporária` ou `migrar`
2. WHEN uma fonte alternativa for usada em texto comum de produto THEN o sistema SHALL tratá-la como desvio a revisar
3. WHEN uma fonte monoespaçada ou de emoji for usada THEN o sistema SHALL reconhecer esse uso como técnico, não como quebra do canon

---

### P2: Guardrails Against New Typography Drift

**User Story**: Como time, queremos guardrails de tipografia para que novas páginas não voltem a introduzir famílias concorrentes.

**Acceptance Criteria**:

1. WHEN um arquivo CSS novo definir `font-family` localmente THEN isso SHALL ser tratado como exceção, não como padrão
2. WHEN a página puder consumir `--font-body` ou `--font-display` THEN ela SHALL preferir esse caminho
3. WHEN uma exceção for mantida THEN ela SHALL ter justificativa explícita

---

## Edge Cases

- WHEN uma superfície usa fonte monoespaçada para valores, logs, IDs ou tracking THEN essa exceção SHALL ser preservada
- WHEN uma superfície usa fontes de emoji ou símbolo THEN isso SHALL ser tratado como suporte de renderização, não como quebra do padrão tipográfico
- WHEN o login estiver em outro dialeto visual histórico THEN a migração SHALL alinhar a tipografia sem reabrir toda a identidade da página
- WHEN um componente antigo depender visualmente de uma família diferente THEN a frente SHALL medir payoff antes de migrar

---

## Risks and Fix Strategy

| Risk | Why it matters | Fix strategy |
| --- | --- | --- |
| Trocar fonte em tudo sem classificar exceções | Pode quebrar usos legítimos de `monospace` e símbolos | Criar matriz de exceções antes da migração |
| Padronização virar rebranding escondido | Pode expandir demais o escopo | Limitar a frente a família tipográfica e hierarquia básica |
| Login puxar uma reforma visual inteira | Pode transformar uma mudança simples em outra obra | Migrar só a família de fonte primeiro |
| Novos arquivos voltarem a sobrescrever `font-family` | A dívida volta rápido | Definir guardrail: tokens primeiro, `font-family` local só com justificativa |

---

## Operational Output Contract

Toda execução ou auditoria desta frente deve:

1. ficar abaixo de **800 palavras por passo**
2. começar com:
   - `Status`
   - `Foco`
   - `Decisao central`
   - `Principal risco`
   - `Proximo passo`
3. separar claramente:
   - o que foi migrado para `Inter`
   - o que foi preservado como exceção saudável
   - o que ficou adiado
4. evitar frases vagas como “tipografia melhorou” sem nomear o arquivo ou a superfície

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| ITS-01 | P1: Inter as Canonical Product Voice | Design | Pending |
| ITS-02 | P1: Inter as Canonical Product Voice | Design | Pending |
| ITS-03 | P1: Product Surfaces Stop Speaking Different Dialects | Design | Pending |
| ITS-04 | P1: Product Surfaces Stop Speaking Different Dialects | Design | Pending |
| ITS-05 | P2: Exception Matrix for Typography | Design | Pending |
| ITS-06 | P2: Exception Matrix for Typography | Design | Pending |
| ITS-07 | P2: Guardrails Against New Typography Drift | Design | Pending |
| ITS-08 | P2: Guardrails Against New Typography Drift | Design | Pending |

**Coverage:** 8 total, 0 mapped to tasks, 8 unmapped warning

---

## Success Criteria

- [ ] `Inter` está declarada e respeitada como fonte canônica das superfícies principais de produto
- [ ] Cards e páginas importantes não usam famílias tipográficas concorrentes sem justificativa
- [ ] Exceções técnicas (`monospace`, emoji, símbolos) estão preservadas e classificadas corretamente
- [ ] A tela de login e outras exceções relevantes têm destino claro: migrar, manter ou justificar
- [ ] Novas páginas ficam menos propensas a criar drift tipográfico

## Success Verdict

Esta frente só é bem-sucedida quando o produto deixa de parecer:

“quase todo em Inter, mas com alguns cantos falando outra língua”

e passa a parecer:

“um sistema com voz tipográfica única, onde cada exceção existe por motivo técnico real”

Metáfora de criança:

Hoje a escola inteira já usa quase o mesmo uniforme, mas alguns alunos ainda vieram com peças antigas.
Esta frente existe para deixar todo mundo com o mesmo uniforme certo, sem tirar o tênis especial de quem precisa correr.
