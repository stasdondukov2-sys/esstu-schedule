from pathlib import Path

from esstu_schedule.catalog import build_catalog
from esstu_schedule.data.diagnostics import parsing_status, reset_diagnostics


def test_missing_catalogs_are_reported(tmp_path):
    reset_diagnostics()
    catalog, institutes, departments = build_catalog(tmp_path, [])
    assert catalog == []
    assert departments == []
    assert all(not value for value in institutes.values())
    status = parsing_status()
    assert status["failed_source_count"] == 2
    assert {item["source"] for item in status["parse_errors"]} == {
        "bakalavriat/craspisanEdt.htm",
        "spezialitet/craspisanEdt.htm",
    }
    reset_diagnostics()


def test_missing_department_is_reported(tmp_path):
    from unittest.mock import patch

    section = tmp_path / "bakalavriat"
    section.mkdir()
    (section / "craspisanEdt.htm").write_text("catalog", encoding="ascii")
    fixture = [
        {"institute": "Test", "departments": [{"caf_id": "Caf5", "name": "Physics"}]}
    ]
    reset_diagnostics()
    with patch(
        "esstu_schedule.catalog.parse_departments_list_html", return_value=fixture
    ):
        build_catalog(Path(tmp_path), [])
    assert "bakalavriat/Caf5.htm" in {
        item["source"] for item in parsing_status()["parse_errors"]
    }
    reset_diagnostics()
