# ADR-012 — Test design: structural asserts > mega-copy asserts

**Status:** Aceito
**Data:** 2026-05-20
**Contexto:** Sprint 4, Bucket C (test_finance_center_renders_dashboard_and_plan_portfolio)

## Decisão

Testes de view que validam render de página **devem** asserir contratos
estruturais, **não** copy/redação. Especificamente:

- Block IDs estáveis usados por JS/anchor links.
- `data-attributes` que coderebs lê (event handlers, controllers JS).
- Anchor `href="#..."` que conecta navegação interna.
- Identificadores de dado (plan name, slug do aluno) + formato BRL/data.
- CTAs com `name="..." value="..."` em forms.

**Não** assertir mais de 5-10 strings de copy/título por test method. Copy
individual fica para snapshot/screenshot regression em outro nível.

## Por quê

`test_finance_center_renders_dashboard_and_plan_portfolio` original tinha
**60+ `assertContains`** de copy do template — cada redação ("Resumo do
recorte ativo", "Fila do turno", "alto risco", "MRR"…). Comportamento real:

- Cada microajuste de copy quebra o teste. Designer trocou "Total MRR" por
  "Receita recorrente"? Test fica vermelho.
- Quando 60+ assertions falham juntas, dev tende a "consertar em lote" com
  busca-substituição cega. Perde-se o sinal: o que realmente mudou no comportamento?
- O test não pega o que IMPORTA: bloco removido por engano, anchor quebrado,
  ID de DOM perdido. Aquilo que JS depende.

Reescrita do mesmo teste:

```python
# Antes: 60+ assertContains de copy.
# Depois: 12 asserts estruturais (block IDs, anchors, data-attrs, plan name + valor).

for block_id in ('finance-trend-preview-board', 'finance-queue-board', ...):
    self.assertContains(response, f'id="{block_id}"')
for mode in ('traditional', 'hybrid', 'ai'):
    self.assertContains(response, f'data-finance-mode-button="{mode}"')
self.assertContains(response, 'Cross Gold')  # plan name
self.assertRegex(response.content.decode(), r'R\$\s*319[,.]90')  # plan price BRL
```

12 asserts cobrem: integridade do DOM, contratos com JS, identidade do dado.
Copy fica para outro nível (snapshot, design QA, prompt review).

## Consequências

- Test simplifica de ~110 linhas para ~50.
- Resiliente a refatorações de copy (designer pode iterar redação sem quebrar
  build).
- Pega regressão REAL: bloco removido, anchor quebrado, data-attr renomeado.
- **Limite explícito:** copy ainda precisa ser validada — em outro lugar:
  - Snapshot tests (django-snapshottest ou similar) podem capturar copy
    estável em arquivo .txt versionado.
  - Visual regression (Percy, BackstopJS) em CI separado.
  - QA de design manual durante review de PR de template.

## Anti-pattern proibido

- `assertContains(response, '<frase exata do template>')` mais de 5x no mesmo
  test method.
- Test method com nome `test_<view>_renders_<thing>` e 50+ linhas — quase sempre
  é mega-screenshot disfarçado.
- Compensar mudança de design adicionando outro `assertContains` no test
  existente; cada string nova é mais frágil que a anterior.

## Referências

- `boxcore/tests/test_finance.py::test_finance_center_renders_dashboard_and_plan_portfolio`
  — exemplo canonical do refactor.
- `docs/testing/quality-plan-prompt.md` Fase 8 — testes de UI futuros
  (snapshot/visual regression).
