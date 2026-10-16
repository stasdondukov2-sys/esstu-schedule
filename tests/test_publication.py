import hashlib
import json
from pathlib import Path

import pytest

from esstu_schedule.catalog import source_metadata, stamp_schedule
from esstu_schedule.data.diagnostics import parsing_status, reset_diagnostics
from esstu_schedule.data.provenance import build_provenance, source_manifest
from esstu_schedule.parser import parse_group_schedule_html
from scripts.check_sync import check_reports


def test_source_fingerprints_are_actual_bytes_and_not_a_new_check(
    tmp_path, monkeypatch
):
    source = tmp_path / "bakalavriat" / "1.htm"
    source.parent.mkdir()
    source.write_bytes(b"old source")
    metadata = {"bakalavriat/1.htm": {"retrieved_at": "2026-10-12T01:00:00Z"}}
    (tmp_path / "sources.json").write_text(json.dumps(metadata))
    manifest = source_metadata(tmp_path, with_hashes=True)
    assert (
        manifest["bakalavriat/1.htm"]["sha256"]
        == hashlib.sha256(b"old source").hexdigest()
    )
    schedule = {"source_file": "bakalavriat/1.htm", "weeks": {}}
    stamp_schedule(schedule, manifest, "2026-10-16T03:00:00Z")
    assert schedule["source_checked_at"] == "2026-10-12T01:00:00Z"
    assert schedule["source_sha256"] == manifest["bakalavriat/1.htm"]["sha256"]
    monkeypatch.setenv("GITHUB_SHA", "1234567890")
    first = build_provenance(manifest, tmp_path)
    assert first["code_revision"] == "1234567890"
    assert first["source_checked_at_latest"] == "2026-10-12T01:00:00+00:00"
    source.write_bytes(b"changed source")
    second = build_provenance(source_manifest(tmp_path, metadata), tmp_path)
    assert first["sources_sha256"] != second["sources_sha256"]


def test_unknown_freshness_stays_unknown(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_SHA", "test")
    result = build_provenance({"file.htm": {"sha256": "a"}}, tmp_path)
    assert result["source_checked_at_latest"] is None
    assert result["sources_without_check_date"] == 1


def test_unparsed_cells_are_counted_separately_from_broken_tables():
    reset_diagnostics()
    html = "<table><tr><td>Пары</td><td>1-я</td></tr><tr><td>Время</td><td>09:00-10:35</td></tr>"
    html += '<tr><td colspan="2">I неделя</td></tr><tr><td>Пнд</td><td>лаб. Иностранный язык а.15-571 а.15-573 а.15-</td></tr></table>'
    schedule = parse_group_schedule_html(html)
    assert not schedule["is_incomplete"]
    status = parsing_status()
    assert status["parse_error_count"] == 0
    assert status["unparsed_cell_count"] == 1


@pytest.mark.parametrize("failed", [[], [{"path": "1.htm", "error": "unavailable"}]])
def test_partial_sync_cannot_succeed_silently(tmp_path, failed):
    for name in ("department-sync.json", "group-sync.json"):
        (tmp_path / name).write_text(
            json.dumps({"downloaded": ["ok.htm"], "failed": failed})
        )
    if failed:
        with pytest.raises(RuntimeError):
            check_reports(tmp_path)
    else:
        check_reports(tmp_path)


def test_mit_license_has_no_placeholders():
    license_text = (Path(__file__).resolve().parents[1] / "LICENSE").read_text(
        encoding="utf-8-sig"
    )
    assert "MIT License" in license_text
    assert "[year]" not in license_text and "[fullname]" not in license_text
