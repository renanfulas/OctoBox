# OctoBox Design Guidelines

## 🎨 Filosofia de Design

### Core Principles

1. **Clareza acima de tudo**
   - Hierarquia visual óbvia
   - Informação organizada logicamente
   - Sem ambiguidade nas ações

2. **Minimalismo funcional**
   - Cada elemento tem propósito
   - Espaço em branco é intencional
   - Simplicidade não é limitação

3. **Premium sem ostentação**
   - Efeitos sutis e refinados
   - Qualidade nos detalhes
   - Sofisticação natural

4. **Autenticidade**
   - Identidade própria
   - Não é uma cópia
   - Personalidade coerente

## 🎯 Sistema de Cores

### Quando usar cada cor

#### 🔴 Vermelho Neon (#ff0844)
**Uso**: Urgente, Crítico, Atenção Imediata
- Alertas críticos
- Ações destrutivas
- Status "Impregnância"
- Badges de urgência

**Não usar para**:
- Elementos decorativos
- Hover states comuns
- Backgrounds grandes

#### 🟡 Amarelo (#ffb020)
**Uso**: Atenção, Warning, Pendente
- Avisos moderados
- Status "Retrasca"
- Itens aguardando ação
- CTAs secundários importantes

**Não usar para**:
- Texto sobre fundo claro
- Estados de sucesso
- Elementos passivos

#### 🟢 Verde (#00ff88)
**Uso**: Sucesso, Meta atingida, Aprovado
- Confirmações
- Status "Meta/rel"
- Trends positivos
- Indicadores de progresso

**Não usar para**:
- Ações destrutivas
- Warnings
- Estados neutros

#### 🔵 Azul (#00d4ff)
**Uso**: Primary, Info, Navegação
- Links e navegação
- Ações primárias
- Informações neutras
- Destaques informativos

**Não usar para**:
- Ações destrutivas
- Estados de erro
- Warnings

#### 🟣 Roxo (#af52de)
**Uso**: Accent, Premium features
- Elementos premium
- Destaques especiais
- Gradientes com azul
- Features VIP

**Não usar para**:
- Ações principais
- Estados críticos
- Navegação básica

### Combinações Recomendadas

✅ **Boas combinações**:
- Azul + Verde (progressão)
- Azul + Roxo (premium)
- Vermelho isolado (crítico)
- Amarelo + Verde (status)

❌ **Evitar**:
- Vermelho + Verde juntos
- Mais de 2 neons no mesmo card
- Todas as cores no mesmo contexto
- Gradientes com >2 cores

## 📐 Espaçamento

### Sistema de Grid
- **Base**: 4px (0.25rem)
- **Pequeno**: 8px (0.5rem)
- **Médio**: 12px (0.75rem)
- **Grande**: 16px (1rem)
- **Extra**: 24px (1.5rem)
- **Section**: 32px (2rem)

### Aplicação

**Padding de Cards**: 24px (1.5rem)
```tsx
<div className="p-6">
```

**Gap entre elementos**: 16px (1rem)
```tsx
<div className="space-y-4">
```

**Margem entre seções**: 32px (2rem)
```tsx
<div className="space-y-8">
```

## 🔤 Tipografia

### Hierarquia

**Display/Hero**: 48px (3rem)
```tsx
<h1 className="text-5xl font-bold">
```

**Título Principal**: 32px (2rem)
```tsx
<h2 className="text-3xl font-bold">
```

**Subtítulo**: 20px (1.25rem)
```tsx
<h3 className="text-xl font-semibold">
```

**Corpo**: 16px (1rem)
```tsx
<p className="text-base">
```

**Small**: 14px (0.875rem)
```tsx
<p className="text-sm">
```

**Tiny**: 12px (0.75rem)
```tsx
<span className="text-xs">
```

### Peso das Fontes

- **Normal**: 400 (texto corrido)
- **Medium**: 500 (labels, subtítulos)
- **Semibold**: 600 (não usar, pular para bold)
- **Bold**: 700 (títulos, números importantes)

### Regras

1. Nunca usar mais de 3 tamanhos no mesmo card
2. Números grandes devem ser bold
3. Labels em uppercase devem ser text-xs
4. Descriptions sempre text-sm ou text-base

## 🎭 Efeitos Visuais

### Glassmorphism

**Quando usar**:
- Cards principais
- Overlays
- Modals
- Popups

**Configuração**:
```css
background: var(--glass-bg);
backdrop-filter: blur(20px);
border: 1px solid var(--glass-border);
```

**Não usar**:
- Buttons
- Small elements
- Texto sobre blur
- Elementos com muita interação

### Neon Glow

**Quando usar**:
- Cards de status
- Hover em cards importantes
- Indicadores de ação
- Badges críticos

**Intensidade**:
- Sutil: 0.1 opacity no outer glow
- Moderado: 0.2 opacity
- Forte: 0.3 opacity (só para crítico)

**Código**:
```tsx
className="shadow-[0_0_20px_rgba(255,8,68,0.15)]"
```

### Borders

**Padrão**: 1px solid var(--border)
```tsx
className="border border-border"
```

**Neon**: 1px com cor específica
```tsx
className="border border-[#ff0844]"
```

**Radius**:
- Pequeno: 8px (rounded-lg)
- Médio: 12px (rounded-xl)
- Grande: 16px (rounded-2xl)
- Hero: 24px (rounded-3xl)

## 🎬 Animações

### Transitions

**Padrão**: 150ms cubic-bezier(0.4, 0, 0.2, 1)

Já aplicado globalmente via CSS:
```css
transition-property: background-color, border-color, color, fill, stroke, opacity, box-shadow, transform;
transition-duration: 150ms;
```

### Hover States

**Scale**: 1.02 para cards
```tsx
className="hover:scale-[1.02] transition-transform"
```

**Opacity**: 0.8 para buttons
```tsx
className="hover:opacity-80"
```

**Background**: Usar variantes definidas
```tsx
className="hover:bg-accent"
```

### Regras

1. Nunca usar transitions > 300ms
2. Sempre ter hover state visível
3. Focus deve ser mais óbvio que hover
4. Disabled deve remover hover

## 📱 Responsividade

### Breakpoints

- **Mobile**: Default (< 768px)
- **Tablet**: md: (768px+)
- **Desktop**: lg: (1024px+)
- **Large**: xl: (1280px+)

### Sidebar

**Desktop**: Fixed width 240px
```tsx
className="w-[240px]"
```

**Mobile**: Drawer (não implementado ainda)
```tsx
// TODO: Implementar drawer
```

### Grids

**Stats Cards**: 1 → 2 → 4 colunas
```tsx
className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
```

**Content**: 1 → 2 colunas
```tsx
className="grid grid-cols-1 md:grid-cols-2 gap-6"
```

## ♿ Acessibilidade

### Focus States

Sempre visível:
```tsx
className="outline-ring/50"
```

### ARIA Labels

Para ícones sem texto:
```tsx
<button aria-label="Toggle theme">
  <Moon className="w-4 h-4" />
</button>
```

### Contraste

Mínimo WCAG AA:
- Normal text: 4.5:1
- Large text: 3:1
- UI elements: 3:1

### Keyboard Navigation

- Tab order lógico
- Enter ativa buttons
- Escape fecha modals
- Arrows navegam listas

## 🚫 O que NÃO fazer

### ❌ Evitar absolutamente

1. **Mais de 2 neons no mesmo card**
   - Fica psicodélico
   - Perde hierarquia

2. **Gradientes com 3+ cores**
   - Parece arco-íris
   - Não é premium

3. **Animations muito rápidas (<100ms)**
   - Parece bugado
   - Causa náusea

4. **Text-shadow em neon**
   - Ilegível
   - Amador

5. **Box-shadow muito forte**
   - Parece flutuando demais
   - Quebra coesão

6. **Borders muito grossas (>2px)**
   - Pesado visualmente
   - Não é moderno

7. **Border-radius inconsistente**
   - Quebra padrão
   - Parece descuidado

### ⚠️ Usar com cautela

1. **Animations complexas**
   - Só se agregar valor
   - Pode distrair

2. **Blur muito forte (>20px)**
   - Performance
   - Legibilidade

3. **Opacity <0.5**
   - Pode ficar invisível
   - Problemas de contraste

4. **Elementos muito pequenos (<32px touch target)**
   - Ruim para mobile
   - Acessibilidade

## ✅ Checklist de Qualidade

Antes de finalizar um componente:

- [ ] Tem hover state?
- [ ] Tem focus state?
- [ ] Funciona no mobile?
- [ ] Cores respeitam o sistema?
- [ ] Espaçamento consistente?
- [ ] Border-radius coerente?
- [ ] Transitions suaves?
- [ ] Contraste adequado?
- [ ] Semantic HTML?
- [ ] Sem neons em excesso?
- [ ] Loading state (se aplicável)?
- [ ] Error state (se aplicável)?
- [ ] Empty state (se aplicável)?

## 📚 Referências de Inspiração

### Stripe
- Minimalismo
- Hierarquia clara
- Espaçamento generoso

### Notion
- Sidebar navegação
- Cards organizados
- Theme toggle

### iOS/Apple
- Glassmorphism
- Blur effects
- Scrollbar discreta
- Rounded corners

### Google Material
- Color system
- Elevation
- Responsive grid

### Linear
- Dark theme premium
- Neon accents sutis
- Shortcuts keyboard

---

**Lembre-se**: O objetivo é criar uma interface **premium, autêntica e minimalista**. Quando em dúvida, simplifique. Menos é mais.
