import json
from unittest.mock import Mock

import pytest

from scripts.check_sync import check_parse_quality
from scripts import sync_departments, sync_esstu


@pytest.mark.parametrize(
    "failed,blocked", [(0, False), (5, False), (6, True), (100, True)]
)
def test_publication_error_rate_limit(tmp_path, failed, blocked):
    (tmp_path / "api").mkdir()
    (tmp_path / "api/status.json").write_text(
        json.dumps({"group_expected_count": 100, "group_failed_count": failed})
    )
    if blocked:
        with pytest.raises(RuntimeError, match="Publication blocked"):
            check_parse_quality(tmp_path, max_error_rate=0.05)
    else:
        check_parse_quality(tmp_path, max_error_rate=0.05)


def test_failed_department_phase_still_refreshes_independent_groups(monkeypatch):
    groups = Mock()
    monkeypatch.setattr(
        sync_esstu, "sync_departments", lambda: {"failed": [{"path": "catalog"}]}
    )
    monkeypatch.setattr(sync_esstu, "sync_groups", groups)
    sync_esstu.sync_all()
    groups.assert_called_once()


@pytest.mark.parametrize(
    "module,entry,expected",
    [(sync_departments, "sync", 2), (sync_esstu, "sync_groups", 4)],
)
def test_unavailable_live_catalog_never_fans_out_over_saved_pages(
    tmp_path, monkeypatch, module, entry, expected
):
    for section in ("bakalavriat", "spezialitet", "zo1", "zo2"):
        directory = tmp_path / section
        directory.mkdir()
        (
            directory / ("craspisanEdt.htm" if entry == "sync" else "raspisan.htm")
        ).write_text("saved catalog must not be used to fan out")
    fetch = Mock(side_effect=OSError("portal timed out"))
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "fetch_page", fetch)
    report = getattr(module, entry)()
    assert fetch.call_count == expected
    assert len(report["failed"]) == expected
    assert not report["downloaded"]
