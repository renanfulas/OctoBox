"""
ARQUIVO: utilitario para deteccao de deriva de esquema (Schema Drift).

POR QUE ELE EXISTE:
- Previne corrupcao de dados ao barrar a restauracao de snapshots (backups de DB) 
  que possuam um esquema estrutural incompativel com o respositorio de codigo atual.

O QUE ESTE ARQUIVO FAZ:
1. Le a tabela `django_migrations` de um arquivo SQLite.
2. Compara com os arquivos de migration físicos `.py` do projeto.
3. Detecta se o snapshot esta atrasado ou possui migracoes "fantasmas" (que nao existem mais no codigo).

PONTOS CRITICOS:
- Snapshot Drift e a maior causa de incidentes apos rollbacks.
"""

import os
import sqlite3
from typing import Dict, List, Set, Tuple

from django.apps import apps
from django.db.migrations.recorder import MigrationRecorder


def get_snapshot_applied_migrations(sqlite_path: str) -> Set[Tuple[str, str]]:
    """
    Extrai a lista de (app, name) das migracoes aplicadas no arquivo SQLite do snapshot.
    """
    if not os.path.exists(sqlite_path):
        raise FileNotFoundError(f"Arquivo de banco não encontrado em: {sqlite_path}")

    try:
        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()
        
        # O snapshot pode ser de uma versao muito antiga onde django_migrations
        # nem exista, prevenindo crash.
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='django_migrations'")
        if not cursor.fetchone():
            return set()
            
        cursor.execute("SELECT app, name FROM django_migrations")
        rows = cursor.fetchall()
        return set((row[0], row[1]) for row in rows)
    finally:
        if 'conn' in locals():
            conn.close()


def get_codebase_migrations() -> Set[Tuple[str, str]]:
    """
    Lista todas as migracoes existentes nos modulos Django instalados.
    Isso diz qual a "verdade" do repositorio Git atual.
    """
    # Acessa os nos da arvore de dependencias reais do Django
    from django.db.migrations.loader import MigrationLoader
    loader = MigrationLoader(None, ignore_no_migrations=True)
    
    # disk_migrations possui um set de tuplas (app_label, migration_name)
    return loader.disk_migrations


def detect_schema_drift(sqlite_path: str) -> Dict[str, List[Tuple[str, str]]]:
    """
    Gera um diff estruturado de divergencia entre um backup e a base de codigo atual.
    
    Retorna:
    {
        'missing_in_snapshot': [(app, name)], # Codigo tem migracoes que o DB não tem
        'ghost_in_snapshot': [(app, name)]    # O DB tem migracoes que o codigo NAO tem mais
    }
    """
    snapshot_migrations = get_snapshot_applied_migrations(sqlite_path)
    code_migrations = get_codebase_migrations()

    missing = sorted(list(code_migrations - snapshot_migrations))
    ghosts = sorted(list(snapshot_migrations - code_migrations))

    return {
        'missing_in_snapshot': missing,
        'ghost_in_snapshot': ghosts
    }


def is_snapshot_safe_to_restore(sqlite_path: str, allow_missing: bool = True) -> Tuple[bool, str]:
    """
    Determina se um snapshot é tecnicamente seguro para entrar em cena.
    
    `allow_missing=True`: permite restaurar um DB mais antigo e imediatamente 
                          rodar as migracoes que faltavam no final do boot.
    """
    drift = detect_schema_drift(sqlite_path)
    
    if drift['ghost_in_snapshot']:
        return False, f"O Snapshot contem {len(drift['ghost_in_snapshot'])} migracoes perdidas/fantasmas. O Git nao conhece essas tabelas/colunas."

    if drift['missing_in_snapshot'] and not allow_missing:
         return False, f"O Snapshot esta obsoleto. Faltam {len(drift['missing_in_snapshot'])} migracoes em relacao ao codigo."

    return True, "Seguro"
