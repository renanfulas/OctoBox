"""
ARQUIVO: utilitário compartilhado de resolução de slug via URL do MuscleWiki.

POR QUE ELE EXISTE:
- Onda A0 (`extract_movements_from_html.py`) e Onda A2 (`parser.py`) precisam
  da MESMA regra de "URL do MuscleWiki -> slug do catálogo" — mesma app,
  mesmo dono, mesmo schema. Duplicar aqui seria a violação de DRY que D.00
  do CORDA reserva pra fronteira ENTRE produtos/apps, não dentro do mesmo
  diretório — por isso isto é um módulo próprio, importado pelos dois.
"""

from __future__ import annotations

from urllib.parse import urlsplit


def movement_slug_from_url(url: str) -> str:
    """'https://musclewiki.com/exercise/barbell-bench-press?model=f' -> 'barbell-bench-press'.

    MuscleWiki usa `?model=f` para o vídeo com modelo feminino — mesmo
    exercício, só a apresentação do vídeo muda. Normaliza fora do slug do
    catálogo (a URL de referência escolhida preserva o que o coach usou).
    """
    path = urlsplit(url).path
    return path.rstrip('/').rsplit('/', 1)[-1]
