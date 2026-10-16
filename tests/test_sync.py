import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sync_departments


class SyncValidationTest(unittest.TestCase):
    def test_invalid_response_preserves_last_good_snapshot(self):
        class Response:
            headers = {}

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def read(self):
                return b"<html>Service temporarily unavailable</html>"

        with tempfile.TemporaryDirectory(
            dir=Path(__file__).resolve().parent
        ) as directory:
            root = Path(directory)
            self.assertEqual(root.resolve().parent, Path(__file__).resolve().parent)
            target = root / "bakalavriat" / "1.htm"
            target.parent.mkdir()
            target.write_bytes(b"last good snapshot")
            with (
                patch.object(sync_departments, "ROOT", root),
                patch("urllib.request.urlopen", return_value=Response()),
            ):
                with self.assertRaises((ValueError, AttributeError)):
                    sync_departments.fetch_page("bakalavriat/1.htm")
            self.assertEqual(target.read_bytes(), b"last good snapshot")


if __name__ == "__main__":
    unittest.main()
