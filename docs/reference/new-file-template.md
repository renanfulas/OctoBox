<!--
ARQUIVO: guia padrao para criacao de novos arquivos do projeto.

TIPO DE DOCUMENTO:
- padrao operacional de documentacao

AUTORIDADE:
- media

DOCUMENTO PAI:
- [reading-guide.md](reading-guide.md)

QUANDO USAR:
- quando a duvida for qual cabecalho, nivel de explicacao e padrao minimo um novo arquivo relevante deve seguir

POR QUE ELE EXISTE:
- garante que novos arquivos nascam com o padrao de documentacao e organizacao definido para a base.

O QUE ESTE ARQUIVO FAZ:
1. mostra o formato esperado para cabecalhos em Python.
2. mostra o formato esperado para cabecalhos em HTML.
3. registra as regras minimas de uso desse padrao.

PONTOS CRITICOS:
- este template orienta consistencia da base inteira e deve permanecer simples e replicavel.
- mudancas aqui afetam o padrao adotado em arquivos novos e revisoes futuras.
-->

# Template para novos arquivos

Use este modelo sempre que criar um arquivo novo relevante no projeto.

## Regra objetiva do cabecalho

Todo arquivo relevante deve abrir com um cabecalho curto, padronizado e fiel ao papel real do arquivo.

Estrutura obrigatoria:

1. ARQUIVO: o que o arquivo e em uma frase curta.
2. POR QUE ELE EXISTE: por que esse arquivo precisa existir separado.
3. O QUE ESTE ARQUIVO FAZ: 2 a 5 responsabilidades concretas.
4. PONTOS CRITICOS: o que pode quebrar, espalhar impacto ou gerar erro silencioso.

Regras de escrita:

1. O cabecalho deve descrever o estado atual do arquivo, nunca uma intencao antiga.
2. O texto deve ser objetivo e operacional, sem linguagem vaga como "arquivo importante" ou "faz varias coisas".
3. O bloco O QUE ESTE ARQUIVO FAZ deve listar responsabilidades reais, nao detalhes de implementacao linha a linha.
4. Se o arquivo mudou de funcao, o cabecalho deve ser atualizado na mesma tarefa.
5. Se o arquivo for pequeno e irrelevante para negocio, utilitario ou fluxo compartilhado, o cabecalho pode ser omitido.

Quando usar comentario interno adicional:

1. Apenas em trechos com regra sensivel, efeito colateral ou decisao nao obvia.
2. O comentario interno deve explicar o porquê do trecho, nao repetir o que a linha ja diz.
3. Evite comentar obviedades ou transformar o arquivo em manual prolixo.

## Para arquivos Python

```python
"""
ARQUIVO: nome e função geral do arquivo.

POR QUE ELE EXISTE:
- motivo da existência do arquivo no projeto.

O QUE ESTE ARQUIVO FAZ:
1. bloco principal 1
2. bloco principal 2
3. bloco principal 3

PONTOS CRITICOS:
- o que é perigoso mexer
- o que pode quebrar se for alterado sem cuidado
"""
```

Exemplo realista para arquivo Python de regra de negocio:

```python
"""
ARQUIVO: workflow de criacao recorrente da grade de aulas.

POR QUE ELE EXISTE:
- tira da view a logica de gerar aulas em lote e validar limites da agenda.

O QUE ESTE ARQUIVO FAZ:
1. gera aulas recorrentes por periodo e dia da semana.
2. evita duplicidade quando o usuario pede para pular horarios existentes.
3. valida limites diario, semanal e mensal antes de cada criacao.
4. registra auditoria do lote criado.

PONTOS CRITICOS:
- qualquer erro aqui pode criar aulas duplicadas ou bloquear a agenda antes da hora.
- mudancas nesta regra impactam tanto a view quanto os testes da grade.
"""
```

## Para arquivos HTML

```html
<!--
ARQUIVO: nome e função geral do template.

POR QUE ELE EXISTE:
- motivo da existência da tela.

O QUE ESTE ARQUIVO FAZ:
1. mostra a área X
2. renderiza a informação Y
3. depende do contexto Z

PONTOS CRITICOS:
- variáveis de contexto que não podem sumir
- partes que impactam várias telas
-->
```

Exemplo realista para template HTML:

```html
<!--
ARQUIVO: central visual de financeiro.

POR QUE ELE EXISTE:
- concentra a leitura financeira e comercial em uma tela operacional fora do admin.

O QUE ESTE ARQUIVO FAZ:
1. mostra indicadores de faturamento, churn e mix de planos.
2. renderiza filtros do recorte financeiro atual.
3. oferece cadastro rapido de planos e acoes operacionais por WhatsApp.

PONTOS CRITICOS:
- depende do contexto montado pela view de financeiro.
- mudancas nos blocos principais impactam leitura gerencial e testes de interface.
-->
```

## Para arquivos CSS

```css
/*
ARQUIVO: papel visual geral do arquivo.

POR QUE ELE EXISTE:
- motivo de esse CSS existir separado do restante.

O QUE ESTE ARQUIVO FAZ:
1. define tokens, componentes ou estilos de uma area especifica.
2. organiza o comportamento responsivo ou visual compartilhado.
3. sustenta os templates que dependem dessas classes.

PONTOS CRITICOS:
- mudancas aqui podem causar regressao visual ampla.
*/
```

Exemplo realista para CSS:

```css
/*
ARQUIVO: extensoes visuais do catalogo.

POR QUE ELE EXISTE:
- complementa o design system base com componentes especificos de alunos, financeiro e grade de aulas.

O QUE ESTE ARQUIVO FAZ:
1. define grids, cards e paineis do catalogo.
2. estiliza componentes da grade, do funil e dos formularios leves.
3. ajusta comportamento responsivo dessas telas.

PONTOS CRITICOS:
- classes alteradas aqui afetam varios templates ao mesmo tempo.
*/
```

## Para arquivos de teste

Arquivos de teste tambem devem ter cabecalho quando cobrirem fluxo relevante, regressao importante ou camada central do produto.

```python
"""
ARQUIVO: testes da area ou fluxo coberto.

POR QUE ELE EXISTE:
- protege uma area operacional contra regressao.

O QUE ESTE ARQUIVO FAZ:
1. testa os cenarios principais da tela ou regra.
2. cobre casos de erro, permissao ou limite quando isso for importante.
3. garante que bugs antigos nao voltem.

PONTOS CRITICOS:
- se estes testes quebrarem, a operacao dessa area perde confianca.
"""
```

Exemplo realista para teste:

```python
"""
ARQUIVO: testes das paginas visuais de catalogo.

POR QUE ELE EXISTE:
- protege a camada leve de alunos, grade e operacao comercial contra regressao.

O QUE ESTE ARQUIVO FAZ:
1. testa renderizacao de alunos e grade de aulas.
2. testa criacao recorrente, limites e edicao rapida da grade.
3. testa conversao de intake, matricula e comunicacao operacional.

PONTOS CRITICOS:
- se estes testes quebrarem, a operacao diaria fora do admin perde cobertura.
"""
```

## Regra de uso

1. Se o arquivo for relevante para negócio, ele deve nascer com cabeçalho.
2. Se a lógica tiver risco de causar bug silencioso, adicione comentário interno curto no bloco sensível.
3. Se o arquivo começar a misturar muitos assuntos, divida antes de crescer.
4. Sempre revise o cabecalho quando o arquivo ganhar novas responsabilidades.
5. Se um arquivo deixar de fazer algo descrito no cabecalho, remova ou reescreva esse trecho na mesma alteração.