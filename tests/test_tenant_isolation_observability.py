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

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse

from access.roles import ROLE_OWNER
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


class SecureExportDownloadIsolationTests(TestCase):
    """SecureExportDownloadView resolve o arquivo NO namespace do box ativo.

    Prova ponta a ponta o fix de seguranca: um box (role OWNER) nao consegue
    baixar o export de OUTRO box mesmo conhecendo o filename exato (IDOR cross-box
    fechado), porque write e read usam o mesmo box_scoped_export_dir().
    """

    def setUp(self):
        call_command('bootstrap_roles')
        user_model = get_user_model()
        self.owner = user_model.objects.create_user('iso_dl_owner', 'iso_dl@test.com')
        self.owner.groups.add(Group.objects.get(name=ROLE_OWNER))
        self.client.force_login(self.owner)

    def _url(self, filename):
        return reverse('api-v1-secure-export-download', kwargs={'filename': filename})

    def test_downloads_own_box_export(self):
        # ignore_cleanup_errors + resp.close(): o FileResponse segura o handle do
        # arquivo aberto; no Windows o tempdir nao consegue apagar enquanto aberto.
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as media, override_settings(MEDIA_ROOT=media):
            own_dir = box_scoped_export_dir(media)  # namespace do box ativo do request
            os.makedirs(own_dir, exist_ok=True)
            with open(os.path.join(own_dir, 'meu.csv'), 'w') as handle:
                handle.write('dados do meu box')
            resp = self.client.get(self._url('meu.csv'))
            status = resp.status_code
            resp.close()
        self.assertEqual(status, 200)

    def test_cannot_download_other_box_export(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as media, override_settings(MEDIA_ROOT=media):
            # arquivo gravado no namespace de OUTRO box
            other_dir = os.path.join(media, 'exports', 'box_de_outro')
            os.makedirs(other_dir, exist_ok=True)
            with open(os.path.join(other_dir, 'segredo.csv'), 'w') as handle:
                handle.write('dados confidenciais de outro box')
            # o box ativo resolve no PROPRIO dir -> nao encontra -> 404
            resp = self.client.get(self._url('segredo.csv'))
        self.assertEqual(resp.status_code, 404)
