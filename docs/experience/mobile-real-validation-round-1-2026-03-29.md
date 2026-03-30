# Reporte de Validação Mobile - Onda 1 (C.O.R.D.A.)

- **Data:** 2026-03-29
- **Status da Rodada:** Finalizada (Auditoria Técnica)
- **Responsável:** Antigravity (Elite Prompt Engineer)

## Resumo Executivo

A auditoria técnica de código (CSS/HTML/JS) para viewports estreitas (320px - 430px) revelou que, embora a estrutura base do shell seja sólida, existem **bloqueadores de layout** na Recepção e no Diretório de Alunos que impedem o uso operacional do Beta em dispositivos móveis sem quebra de interface.

---

## 1. Janela de Resultados por Superfície

| Superfície | Status | Ponto Crítico | Decisão |
| :--- | :--- | :--- | :--- |
| **Shell Global** | ⚠️ Tolerável | Topbar empilha em 1240px (perda de espaço vertical rápida). | Manter (Ajustar Onda 2) |
| **Login & Busca** | ✅ OK | Inputs com boa área de toque. | Manter |
| **Recepção** | 🚫 Bloqueador | Grid fixo com `minmax(320px)` estoura o layout no celular. | **Corrigir antes de seguir** |
| **Diretório Alunos** | ⚠️ Tolerável | Grid de KPIs fixo em 4 colunas esmaga o conteúdo no mobile. | **Corrigir antes de seguir** |

---

## 2. Detalhamento Técnico e Bloqueadores

### 🚫 BLOQUEADOR: Grid da Recepção (`reception/scene.css`)
- **Evidência:** `grid-template-columns: minmax(0, 1.05fr) minmax(320px, 0.95fr);`
- **Impacto:** Em um iPhone SE (320px) ou iPhone 14 (390px), a soma das colunas + gap extrapola a viewport. A coluna da esquerda desaparece ou gera scroll horizontal infinito quebrado.
- **Risco:** Inviabiliza o uso do "balcão" (check-in) via smartphone.

### ⚠️ AVISO: Grid de KPIs dos Alunos (`catalog/students.html`)
- **Evidência:** `class="grid grid-cols-4 gap-6"` sem media queries de empilhamento.
- **Impacto:** 4 colunas em 320px resultam em cards de aproximadamente 70px de largura. Texto de KPIs ficará ilegível/cortado.
- **Risco:** Perda total de legibilidade estratégica na entrada do diretório.

### ⚠️ FRICÇÃO: Sidebar Toggle (`base.html` / `topbar.css`)
- **Evidência:** Botão de toggle é apenas texto ("Menu") e visível no desktop.
- **Impacto:** Colisão visual na Topbar em 1240px quando a sidebar já está visível. Estética "MVP antigo".
- **Risco:** Baixa percepção de "Premium" (Stripe Elite).

---

## 3. Próximos Passos Recomendados

Para fechar a **Onda 1** e transitar para a **Onda 2 (Ações)**, recomendo:

1.  **Refactor da Recepção:** Mudar para `grid-template-columns: 1fr` em viewports < 1024px.
2.  **Refactor de KPIs:** Implementar `grid-cols-1` ou `grid-cols-2` para mobile no catálogo de alunos.
3.  **Upgrade do Toggle:** Trocar o texto "Menu" por um ícone (hamburger) e esconder o botão em larguras onde a sidebar é `sticky`.

> [!IMPORTANT]
> **Aprovação para Onda 2:** Deseja que eu inicie as correções destes bloqueadores imediatamente ou quer revisar a estratégia de layout primeiro?
