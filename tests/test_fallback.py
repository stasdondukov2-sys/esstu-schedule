import hashlib
import json
from unittest.mock import patch

import pytest

from esstu_schedule import app, cache_tools


@pytest.mark.parametrize("filename", ["raspisan.htm", "craspisanEdt.htm", "Caf5.htm"])
def test_disabled_html_fallback_reaches_service_snapshot(tmp_path, filename):
    source = tmp_path / "bakalavriat" / filename
    source.parent.mkdir()
    source.write_bytes(b"old local HTML")
    with (
        patch.object(app, "DEMO_DIR", tmp_path),
        patch.object(app.urllib.request, "urlopen", side_effect=OSError("offline")),
        pytest.raises(RuntimeError, match="недоступен"),
    ):
        app.fetch_esstu_html_sync(f"bakalavriat/{filename}", allow_group_fallback=False)


def test_allowed_html_fallback_preserves_date_and_hash(tmp_path):
    source = tmp_path / "bakalavriat" / "1.htm"
    source.parent.mkdir()
    source.write_bytes(b"saved HTML")
    (tmp_path / "sources.json").write_text(
        json.dumps({"bakalavriat/1.htm": {"retrieved_at": "2026-10-12T01:00:00Z"}})
    )
    with (
        patch.object(app, "DEMO_DIR", tmp_path),
        patch.object(app.urllib.request, "urlopen", side_effect=OSError("offline")),
    ):
        page = app.fetch_esstu_html_sync("bakalavriat/1.htm")
    assert page.source_mode == "local_fallback"
    assert page.checked_at == "2026-10-12T01:00:00Z"
    assert page.source_sha256 == hashlib.sha256(b"saved HTML").hexdigest()


def test_groups_use_saved_json_when_live_catalog_is_unavailable(tmp_path):
    source = tmp_path / "bakalavriat" / "raspisan.htm"
    source.parent.mkdir()
    source.write_bytes(b"old local catalog must not replace saved JSON")
    snapshot = {
        "section": "bakalavriat",
        "groups": [{"id": "7", "name": "Saved group"}],
        "source_mode": "saved_snapshot",
        "source_checked_at": "2026-10-12T01:00:00Z",
        "is_stale_fallback": True,
    }
    app.CACHE.clear()
    cache_tools._service_cache.clear()
    try:
        with (
            patch.object(app, "DEMO_DIR", tmp_path),
            patch.object(app.urllib.request, "urlopen", side_effect=OSError("offline")),
            patch.object(app, "load_snapshot", return_value=snapshot) as load,
            patch.object(app, "save_snapshot") as save,
        ):
            result = app.service_groups("bakalavriat", force_refresh=True)
        assert result == snapshot
        load.assert_called_once_with("groups:bakalavriat")
        save.assert_not_called()
    finally:
        app.CACHE.clear()
        cache_tools._service_cache.clear()
