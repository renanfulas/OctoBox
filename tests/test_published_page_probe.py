import unittest

from shared_support.published_page_probe import (
    extract_current_page_behavior,
    extract_json_script_text,
    summarize_published_html_probe,
)


class PublishedPageProbeTests(unittest.TestCase):
    def test_extract_current_page_behavior_reads_json_script_payload(self):
        html = """
        <html>
          <body>
            <script id="current-page-behavior" type="application/json">
              {"directory_search":{"index":[{"id":1},{"id":2}],"total":23,"has_next":true},"performance_timing":{"listing_duration_ms":8.5,"support_duration_ms":4.3,"total_view_duration_ms":31.35}}
            </script>
          </body>
        </html>
        """

        payload = extract_current_page_behavior(html)

        self.assertEqual(payload["directory_search"]["total"], 23)
        self.assertEqual(payload["performance_timing"]["total_view_duration_ms"], 31.35)

    def test_summarize_published_html_probe_exposes_payload_metrics(self):
        html = """
        <html>
          <body>
            <script id="current-page-behavior" type="application/json">
              {"directory_search":{"index":[{"id":1},{"id":2},{"id":3}],"total":23,"has_next":true},"performance_timing":{"listing_duration_ms":8.5,"support_duration_ms":4.3,"total_view_duration_ms":31.35}}
            </script>
          </body>
        </html>
        """

        summary = summarize_published_html_probe(
            url="https://example.com/alunos/",
            status_code=200,
            html=html,
            headers={
                "Content-Type": "text/html; charset=utf-8",
                "Content-Encoding": "gzip",
                "Cache-Control": "private, max-age=0",
            },
            request_elapsed_ms=118.456,
            encoded_body_bytes=2048,
        )

        self.assertEqual(summary["status_code"], 200)
        self.assertEqual(summary["request_elapsed_ms"], 118.46)
        self.assertEqual(summary["encoded_body_bytes"], 2048)
        self.assertTrue(summary["current_page_behavior_present"])
        self.assertEqual(summary["directory_search_index_entries"], 3)
        self.assertEqual(summary["directory_search_total"], 23)
        self.assertTrue(summary["directory_search_has_next"])
        self.assertEqual(summary["listing_snapshot_ms"], 8.5)
        self.assertEqual(summary["support_snapshot_ms"], 4.3)
        self.assertEqual(summary["view_total_ms"], 31.35)
        self.assertEqual(summary["headers"]["content_encoding"], "gzip")

    def test_extract_json_script_text_returns_none_when_payload_absent(self):
        self.assertIsNone(extract_json_script_text("<html><body>sem payload</body></html>"))
