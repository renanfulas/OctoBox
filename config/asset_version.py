"""Versão dos assets estáticos (?v= e nome do cache do service worker).

Ordem: `STATIC_ASSET_VERSION` explícita > SHA da release (`OCTOBOX_RELEASE_SHA`,
gravado pelo deploy da VPS no `.release.env`; `RENDER_GIT_COMMIT` da era do
Render) > '1'. Com o SHA, cada deploy troca a versão sozinho: o navegador
baixa o CSS/JS novo e o PWA instalado re-precacheia, sem depender do bump
manual de `PUBLIC_WORKOUT_CACHE_EPOCH` (que fica só para expurgo de
segurança). '1' é o sinal de "não configurado": os consumidores caem no
mtime dos arquivos (access/context_processors.py, public_workout_pwa.py).
"""

from __future__ import annotations

from collections.abc import Mapping

UNCONFIGURED = '1'


def static_asset_version(environ: Mapping[str, str]) -> str:
    explicit = (environ.get('STATIC_ASSET_VERSION') or '').strip()
    if explicit:
        return explicit
    for name in ('OCTOBOX_RELEASE_SHA', 'RENDER_GIT_COMMIT'):
        sha = (environ.get(name) or '').strip().lower()
        if sha:
            return sha[:12]
    return UNCONFIGURED
