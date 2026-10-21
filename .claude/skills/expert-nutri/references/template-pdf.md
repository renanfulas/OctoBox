# Template de PDF — padrão visual dos planos alimentares

Este projeto gera planos alimentares em PDF com **reportlab/platypus**
(não HTML→PDF), no seguinte padrão visual (nasceu do ajuste do plano da
Franciele Munhoz, primeira vez que esta skill foi usada):

- Capa: título "Plano alimentar" + nome do cliente + nota sobre origem do
  plano (se adaptado de um nutricionista terceiro) e a estratégia de ajuste
  aplicada, com disclaimer de que não é uma nova prescrição clínica.
- Cada refeição em página própria (ou compartilhando página quando curta):
  faixa verde (`#AFCB99`) com o nome da refeição + horário, seguida das
  opções numeradas em bullet, medida caseira sempre antes da grama entre
  parênteses.
- Quando a refeição tem estrutura "base + escolha de proteína + legumes +
  salada" (like almoço), usar uma tabela de 3 colunas com cabeçalho em verde
  claro (`#E9F2E2`) — ver `resumo_ajuste_table`/estrutura de tabela no
  `template_plano.py`.
- Última página: "Orientações" (bullets, igual ao plano original + nota do
  ajuste aplicado) seguida de uma tabela **"Resumo do ajuste calórico
  (referência interna)"** — antes/depois/redução por refeição + total do
  dia, com nota de rodapé sobre a limitação da estimativa (itens não
  listados como óleo de preparo).

**Use `references/template_plano.py` como ponto de partida** — copie o
arquivo, ajuste `OUT_PATH` e o conteúdo de cada seção. As funções
`meal_header()`, `option_block()` e `resumo_ajuste_table()` são genéricas,
não precisam ser reescritas.

## Decisões de design (e por quê)

- **Nunca copiar logo/fotos de estoque do nutricionista original** — o
  documento gerado é uma adaptação derivada para uso interno/do próprio
  cliente, não uma falsificação visual do documento original de terceiros.
  Cores similares (verde suave) são estilo, não identidade visual protegida.
- **Tabela de resumo calórico vai só no final**, separada das páginas de uso
  diário — quem for usar o plano no dia a dia não precisa ver número de
  kcal, só a refeição; o registro numérico é para quem aprovou o ajuste
  (o coach/nutricionista), não para o cliente final se perder em números.
- **`ROUNDEDCORNERS` no `TableStyle`** é suportado nas versões recentes do
  reportlab para dar cantos arredondados na faixa verde — se o ambiente
  tiver uma versão antiga e isso quebrar, remova essa linha do
  `TableStyle` (a faixa colorida ainda funciona sem cantos arredondados).

## Dependência

```bash
pip install reportlab
```
Verifique se já está instalado antes (`python3 -c "import reportlab"`) —
neste projeto normalmente não está, precisa instalar na sessão.
