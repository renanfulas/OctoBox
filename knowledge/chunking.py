"""
ARQUIVO: estrategia de chunking do conhecimento interno.

POR QUE ELE EXISTE:
- transforma arquivos do repositorio em blocos recuperaveis sem depender de bibliotecas externas de embeddings.

O QUE ESTE ARQUIVO FAZ:
1. quebra markdown por heading e tamanho.
2. quebra codigo e texto por janelas previsiveis de linhas.
3. devolve chunks explainable com heading e faixa de linhas.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


TOKEN_RE = re.compile(r"[a-z0-9_]{2,}", re.IGNORECASE)
HEADING_RE = re.compile(r'^\s{0,3}#{1,6}\s+(?P<title>.+?)\s*$')
CODE_ANCHOR_RE = re.compile(r'^\s*(class|def)\s+[A-Za-z_][A-Za-z0-9_]*')

MAX_MARKDOWN_CHARS = 1200
WINDOW_SIZE_LINES = 40
WINDOW_OVERLAP_LINES = 8


@dataclass(slots=True)
class ChunkDraft:
    heading: str
    content: str
    start_line: int
    end_line: int
    token_count: int
    metadata: dict


def _count_tokens(text: str) -> int:
    return len(TOKEN_RE.findall(text.lower()))


def _preview(text: str) -> str:
    compact = ' '.join(text.split())
    return compact[:280]


def chunk_file(*, path: str, content: str, extension: str) -> list[ChunkDraft]:
    if extension == '.md':
        return _chunk_markdown(path=path, content=content)
    return _chunk_windowed(path=path, content=content)


def _chunk_markdown(*, path: str, content: str) -> list[ChunkDraft]:
    lines = content.splitlines()
    chunks: list[ChunkDraft] = []
    current_heading = ''
    buffer: list[str] = []
    start_line = 1

    def flush(end_line: int):
        nonlocal buffer, start_line
        text = '\n'.join(buffer).strip()
        if not text:
            buffer = []
            start_line = end_line + 1
            return
        chunks.append(
            ChunkDraft(
                heading=current_heading,
                content=text,
                start_line=start_line,
                end_line=end_line,
                token_count=_count_tokens(text),
                metadata={'path': path, 'preview': _preview(text)},
            )
        )
        buffer = []
        start_line = end_line + 1

    for index, line in enumerate(lines, start=1):
        heading_match = HEADING_RE.match(line)
        if heading_match:
            flush(index - 1)
            current_heading = heading_match.group('title').strip()
            start_line = index
            buffer = [line]
            continue

        candidate = '\n'.join([*buffer, line]).strip()
        if buffer and len(candidate) > MAX_MARKDOWN_CHARS:
            flush(index - 1)
            buffer = [line]
            start_line = index
            continue

        buffer.append(line)

    flush(len(lines))
    return [chunk for chunk in chunks if chunk.content.strip()]


def _chunk_windowed(*, path: str, content: str) -> list[ChunkDraft]:
    lines = content.splitlines()
    if not lines:
        return []

    chunks: list[ChunkDraft] = []
    start = 0
    while start < len(lines):
        end = min(len(lines), start + WINDOW_SIZE_LINES)
        window = lines[start:end]
        text = '\n'.join(window).strip()
        if text:
            heading = ''
            for candidate in window:
                if CODE_ANCHOR_RE.match(candidate):
                    heading = candidate.strip()
                    break
            chunks.append(
                ChunkDraft(
                    heading=heading,
                    content=text,
                    start_line=start + 1,
                    end_line=end,
                    token_count=_count_tokens(text),
                    metadata={'path': path, 'preview': _preview(text)},
                )
            )
        if end >= len(lines):
            break
        start = max(end - WINDOW_OVERLAP_LINES, start + 1)
    return chunks

