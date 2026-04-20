"""
ARQUIVO: utilitarios vetoriais do RAG interno.

POR QUE ELE EXISTE:
- permite armazenar embeddings de forma portavel entre SQLite e PostgreSQL.
- evita JSON gigante e reduz payload persistido.

O QUE ESTE ARQUIVO FAZ:
1. empacota vetores float32 em bytes.
2. desempacota bytes em floats.
3. calcula norma e similaridade de cosseno.
"""

from __future__ import annotations

import math
import struct


def pack_vector(values: list[float]) -> bytes:
    if not values:
        return b''
    return struct.pack(f'<{len(values)}f', *values)


def unpack_vector(blob: bytes) -> list[float]:
    if not blob:
        return []
    size = len(blob) // 4
    return list(struct.unpack(f'<{size}f', blob))


def vector_norm(values: list[float]) -> float:
    return math.sqrt(sum(value * value for value in values))


def cosine_similarity(*, left: list[float], right_blob: bytes, right_norm: float) -> float:
    if not left or not right_blob or not right_norm:
        return 0.0
    right = unpack_vector(right_blob)
    if len(left) != len(right):
        return 0.0
    left_norm = vector_norm(left)
    if not left_norm:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    return dot / (left_norm * right_norm)
