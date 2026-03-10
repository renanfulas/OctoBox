# Template para novos arquivos

Use este modelo sempre que criar um arquivo novo relevante no projeto.

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

## Regra de uso

1. Se o arquivo for relevante para negócio, ele deve nascer com cabeçalho.
2. Se a lógica tiver risco de causar bug silencioso, adicione comentário interno curto no bloco sensível.
3. Se o arquivo começar a misturar muitos assuntos, divida antes de crescer.