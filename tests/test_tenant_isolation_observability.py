"""
ARQUIVO: testes do isolamento de observabilidade por box (Topic 2 / Risco #2 do
CORDA da Fase 1 — "isolamento pela metade").

POR QUE EXISTE:
- Os DADOS ja sao isolados por schema; o que faltava era carimbar/namespacear os
  ARTEFATOS transversais: logs, exports (download) e storage (arquivos em disco).
- Prova, em especial, o isolamento de STORAGE por construcao: write (task) e read
  (download view) usam o MESMO helper com o slug do box ativo, entao um box nao
  alcanca o arquivo de outro mesmo conhecendo o filename (fecha IDOR cross-box).

ESTRATEGIA:
- `_as_box(slug)` seta `connection.schema_name` direto (o que get_box_runtime_slug
  le) sem exigir que o schema exista — testa a logica de identidade de runtime
  isoladamente.
"""

from __future__ import annotations

import logging
import os
import tempfile
from contextlib import contextmanager

from django.db import connection
from django.test import TestCase

from shared_support.box_log_filter import BoxRuntimeLogFilter
from shared_support.box_runtime import box_scoped_export_dir, box_scoped_filename


@contextmanager
def _as_box(slug):
    """Simula 'box <slug> ativo' setando connection.schema_name (o que o runtime le)."""
    prev = getattr(connection, 'schema_name', None)
    connection.schema_name = slug
    try:
        yield
    finally:
        connection.schema_name = prev


class BoxScopedFilenameTests(TestCase):

    def test_prefixes_with_active_box_slug(self):
        with _as_box('box_alpha'):
            self.assertEqual(box_scoped_filename('alunos.csv'), 'box_alpha_alunos.csv')
        with _as_box('box_beta'):
            self.assertEqual(box_scoped_filename('alunos.csv'), 'box_beta_alunos.csv')

    def test_idempotent_within_same_box(self):
        with _as_box('box_alpha'):
            once = box_scoped_filename('alunos.csv')
            self.assertEqual(box_scoped_filename(once), once)

    def test_empty_filename_falls_back(self):
        with _as_box('box_alpha'):
            self.assertEqual(box_scoped_filename(''), 'box_alpha_export')


class BoxScopedExportDirTests(TestCase):

    def test_dir_isolated_per_box(self):
        with _as_box('box_alpha'):
            a = box_scoped_export_dir('/srv/media')
        with _as_box('box_beta'):
            b = box_scoped_export_dir('/srv/media')
        self.assertNotEqual(a, b)
        self.assertTrue(a.endswith(os.path.join('exports', 'box_alpha')))
        self.assertTrue(b.endswith(os.path.join('exports', 'box_beta')))

    def test_cross_box_storage_isolation_by_construction(self):
        """box_beta nao resolve um arquivo escrito por box_alpha (mesma logica
        exata do write na task e do read no SecureExportDownloadView)."""
        with tempfile.TemporaryDirectory() as media_root:
            with _as_box('box_alpha'):
                alpha_dir = box_scoped_export_dir(media_root)
                os.makedirs(alpha_dir, exist_ok=True)
                with open(os.path.join(alpha_dir, 'secret.csv'), 'w') as f:
                    f.write('dados do box alpha')

            # box_beta tenta o MESMO filename -> resolve no proprio namespace -> 404
            with _as_box('box_beta'):
                beta_path = os.path.join(box_scoped_export_dir(media_root), 'secret.csv')
                self.assertFalse(os.path.exists(beta_path))

            # box_alpha resolve e encontra o proprio
            with _as_box('box_alpha'):
                alpha_path = os.path.join(box_scoped_export_dir(media_root), 'secret.csv')
                self.assertTrue(os.path.exists(alpha_path))


class BoxRuntimeLogFilterTests(TestCase):

    def test_injects_active_box_slug_into_record(self):
        log_filter = BoxRuntimeLogFilter()
        record = logging.LogRecord('octobox.x', logging.INFO, __file__, 1, 'msg', None, None)
        with _as_box('box_gamma'):
            self.assertTrue(log_filter.filter(record))
        self.assertEqual(record.runtime_slug, 'box_gamma')

    def test_filter_never_leaves_slug_unset(self):
        log_filter = BoxRuntimeLogFilter()
        record = logging.LogRecord('octobox.x', logging.INFO, __file__, 1, 'msg', None, None)
        self.assertTrue(log_filter.filter(record))
        self.assertTrue(getattr(record, 'runtime_slug', ''))


class HttpExportFilenameTests(TestCase):

    def test_csv_response_filename_is_box_scoped(self):
        from reporting.infrastructure.http_exports import build_csv_response
        with _as_box('box_delta'):
            resp = build_csv_response(filename='relatorio.csv', headers=['a'], rows=[['1']])
        self.assertIn('box_delta_relatorio.csv', resp['Content-Disposition'])

    def test_pdf_response_filename_is_box_scoped(self):
        from reporting.infrastructure.http_exports import build_pdf_response
        with _as_box('box_delta'):
            resp = build_pdf_response(filename='relatorio.pdf', title='T', sections=[])
        self.assertIn('box_delta_relatorio.pdf', resp['Content-Disposition'])
