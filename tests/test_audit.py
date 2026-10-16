import http.client
import json
import ssl
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup

import app
import parser
from cache_tools import TTLCache, singleflight


class ReliabilityTests(unittest.TestCase):
    def test_ambiguous_room_assignments_are_explicit(self):
        raw = "лаб. Иностранный язык а.15-571 а.15-573 а.15-"
        lesson = parser.parse_single_lesson_chunk(raw)
        self.assertTrue(lesson["parse_warning"])
        self.assertEqual(lesson["room"], "")
        self.assertEqual(lesson["teacher"], "")
        self.assertEqual(lesson["raw"], raw)

    def test_merge_preserves_extra_pairs_and_missing_weeks(self):
        pair = {
            "number": 1,
            "start": "09:00",
            "end": "10:35",
            "lessons": [{"raw": "A", "subject": "A"}],
        }
        late = {
            "number": 7,
            "start": "19:45",
            "end": "21:20",
            "lessons": [{"raw": "B", "subject": "B"}],
        }
        primary = {"weeks": {"1": {"monday": {"pairs": [pair]}}}}
        secondary = {
            "weeks": {
                "1": {"monday": {"pairs": [pair, late]}},
                "2": {"tuesday": {"pairs": [late]}},
            }
        }
        before = deepcopy(secondary)
        merged = parser.merge_teacher_schedules(primary, secondary)
        self.assertEqual(len(merged["weeks"]["1"]["monday"]["pairs"]), 2)
        self.assertEqual(len(merged["weeks"]["1"]["monday"]["pairs"][0]["lessons"]), 1)
        self.assertIn("tuesday", merged["weeks"]["2"])
        merged["weeks"]["2"]["tuesday"]["pairs"][0]["lessons"].clear()
        self.assertEqual(secondary, before)

    def test_dates_do_not_invent_weekdays_or_overwrite_rows(self):
        self.assertIsNone(parser.parse_day_or_date_cell("31.02", 0))
        first = parser.parse_day_or_date_cell("15 янв", 0)
        self.assertEqual(first[0], "date_15.01")
        self.assertEqual(first[3], -1)
        self.assertNotIn("Понедельник", first[1])
        self.assertEqual(
            parser.parse_day_or_date_cell("Пнд,14 сентября", 0)[4], "14.09"
        )
        self.assertEqual(
            parser.parse_day_or_date_cell("16.01.2026", 0)[4], "16.01.2026"
        )
        html = "<table><tr><td>День</td><td>1</td></tr><tr><td></td><td>09:00 - 10:35</td></tr>"
        html += (
            "".join(
                f"<tr><td>{date}.01</td><td>экз. Физика</td></tr>"
                for date in range(10, 18)
            )
            + "</table>"
        )
        parsed = parser.parse_14row_table(BeautifulSoup(html, "html.parser").table)
        self.assertEqual(len(parsed["weeks"]["1"]), 8)
        self.assertEqual(parsed["weeks"]["2"], {})

    def test_spacer_rows_do_not_change_week(self):
        html = "<table><tr><td></td><td>1</td></tr><tr><td></td><td>09:00 - 10:35</td></tr>"
        html += "<tr><td>Пнд</td><td>лек. A</td></tr>" + "<tr><td></td></tr>" * 10
        html += "<tr><td>Втр</td><td>лек. B</td></tr><tr><td>Пнд</td><td>лек. C</td></tr></table>"
        with self.assertRaises(parser.ScheduleStructureError):
            parser.parse_14row_table(BeautifulSoup(html, "lxml").table)

    def test_missing_teacher_heading_is_not_a_person(self):
        with self.assertLogs("esstu_schedule", level="WARNING"):
            self.assertEqual(
                parser.parse_department_teachers_html(
                    "<table><tr><td>A</td></tr></table>"
                ),
                [],
            )

    def test_meta_cache_and_explicit_invalidation(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            path = Path(directory) / "meta.json"
            path.write_text("{}", encoding="utf-8")
            parser._read_teachers_meta.cache_clear()
            with patch.object(parser, "TEACHERS_META_PATH", path):
                for _ in range(10):
                    parser.build_teacher_profile("Иванов И.И.")
                self.assertEqual(parser._read_teachers_meta.cache_info().misses, 1)
                parser.save_teacher_meta_entry("Иванов И.И.", {"degree": "Updated"})
                self.assertEqual(
                    parser.build_teacher_profile("Иванов И.И.")["degree"], "Updated"
                )

    def test_cache_coalesces_concurrent_work(self):
        cache, calls = TTLCache(), []

        @singleflight
        def work(key="A"):
            cached = cache.get(key, 900)
            if cached is not None:
                return cached
            calls.append(key)
            time.sleep(0.02)
            cache.put(key, {"value": key})
            return cache.get(key, 900)

        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(len(list(pool.map(lambda _: work(), range(8)))), 8)
        self.assertEqual(calls, ["A"])

    def test_fallback_is_structured_and_preserves_dates(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root = Path(directory)
            (root / "bakalavriat").mkdir()
            (root / "bakalavriat/1.htm").write_text("saved", encoding="cp1251")
            (root / "sources.json").write_text(
                json.dumps(
                    {
                        "bakalavriat/1.htm": {
                            "retrieved_at": "2026-01-01T00:00:00Z",
                            "last_modified": "Mon, 01 Jan 2024 00:00:00 GMT",
                        }
                    }
                )
            )
            with (
                patch.object(app, "DEMO_DIR", root),
                patch("urllib.request.urlopen", side_effect=OSError("offline")),
                self.assertLogs(app.LOGGER),
            ):
                page = app.fetch_esstu_html_sync("bakalavriat/1.htm")
            payload = app.apply_page_status({}, page)
            self.assertTrue(payload["is_stale_fallback"])
            self.assertEqual(payload["source_checked_at"], "2026-01-01T00:00:00Z")
            self.assertEqual(payload["last_modified"], "Mon, 01 Jan 2024 00:00:00 GMT")
        self.assertEqual(app.SSL_CONTEXT.verify_mode, ssl.CERT_REQUIRED)


class HTTPRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        root = Path(cls.directory.name)
        assert root.resolve().parent == Path(__file__).resolve().parent
        cls.static = root / "static"
        cls.static.mkdir()
        (cls.static / "index.html").write_text("<html>ok</html>")
        (cls.static / "image.png").write_bytes(b"png")
        (root / "static_evil").mkdir()
        (root / "static_evil/secret").write_text("private")
        cls.patch = patch.object(app, "STATIC_DIR", cls.static)
        cls.patch.start()
        cls.server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.ESSTURequestHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.patch.stop()
        cls.directory.cleanup()

    def request(self, path, headers=None, method="GET", body=None):
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=3)
        connection.request(method, path, body, headers or {})
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_routing_and_traversal(self):
        for path in ["/api/schedule/x", "/api/department/x"]:
            self.assertEqual(self.request(path)[0], 400)
        for path in [
            "/../static_evil/secret",
            "/%2e%2e/static_evil/secret",
            "/missing.js",
            "/api/unknown",
        ]:
            status, _, body = self.request(path)
            self.assertEqual(status, 404)
            self.assertNotIn(b"private", body)
        self.assertEqual(self.request("/api/groups?section=invalid")[0], 400)

    def test_etag_and_binary_mime(self):
        status, headers, body = self.request("/image.png")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "image/png")
        status, _, body = self.request("/image.png", {"If-None-Match": headers["ETag"]})
        self.assertEqual(status, 304)
        self.assertEqual(body, b"")

    def test_invalid_json_body(self):
        self.assertEqual(
            self.request("/api/teacher/meta", method="POST", body="{")[0], 405
        )
        self.assertEqual(
            self.request("/api/teacher/meta", method="POST", body="[]")[0], 405
        )

    def test_status_exposes_parser_diagnostics(self):
        from esstu_schedule.data.diagnostics import parsing_status, record_error

        previous = parsing_status()["parse_error_count"]
        with self.assertLogs("esstu_schedule", level="WARNING"):
            record_error("test.htm", "Unexpected structure")
        status, _, body = self.request("/api/status")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["parse_error_count"], previous + 1)

    def test_rooms_route_reads_prebuilt_snapshot(self):
        import os

        from esstu_schedule.data.store import write_json_atomic

        path = self.static.parent / "rooms.json"
        write_json_atomic(path, {"count": 1, "rooms": [{"room": "0410", "slots": {}}]})
        with (
            patch.dict(os.environ, {"ESSTU_ROOMS_INDEX": str(path)}),
            patch.object(
                app, "service_all_teachers", side_effect=AssertionError("Must not scan")
            ),
        ):
            status, _, body = self.request("/api/rooms")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["rooms"][0]["room"], "0410")


if __name__ == "__main__":
    unittest.main()
