import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock
from urllib.error import HTTPError

import pytest
from esstu_schedule.parser import (
    parse_group_schedule_html,
    parse_department_teachers_html,
    repair_mojibake,
)
from scripts import sync_departments
from scripts.check_sync import check_parse_quality
from scripts.publication import last_good_group, reuse_api, source_is_recent

FIXTURES = Path(__file__).parent / "fixtures"


def test_real_headings_do_not_depend_on_font_colour():
    html = (FIXTURES / "zo1-24.htm").read_bytes().decode("cp1251")
    original = parse_group_schedule_html(html, "24", "zo1")
    assert original["group_name"] == "ЗУ-424-2"
    changed = parse_group_schedule_html(html.replace("#ff00ff", "#123456"), "24", "zo1")
    assert changed == original
    assert not changed["is_incomplete"]


def test_real_caf48_mixed_encoding_has_complete_teachers():
    raw = (FIXTURES / "spezialitet-Caf48.htm").read_bytes()
    teachers = parse_department_teachers_html(
        raw.decode("cp1251"), "Caf48", "spezialitet"
    )
    assert teachers and all(not teacher["is_incomplete"] for teacher in teachers)
    assert any("Скуратова" in teacher["profile"]["short_name"] for teacher in teachers)
    assert repair_mojibake("Р§С‚РІ") == "Чтв"
    assert repair_mojibake("РџРЅРґ") == "Пнд"
    assert repair_mojibake("История России Иванов И.И.") == "История России Иванов И.И."
    for fixture in json.loads(
        (FIXTURES / "review-manifest.json").read_text(encoding="utf-8")
    ):
        assert (
            hashlib.sha256((FIXTURES / fixture["fixture"]).read_bytes()).hexdigest()
            == fixture["sha256"]
        )


@pytest.mark.parametrize("age,used", [(0, True), (7, True), (8, False), (None, False)])
def test_group_fallback_has_identity_and_seven_day_expiry(age, used):
    now = datetime(2026, 10, 17, tzinfo=UTC)
    candidate = {
        "group_id": "new",
        "group_name": "A",
        "is_incomplete": True,
        "parse_errors": ["missing"],
    }
    old = {
        "group_id": "old",
        "group_name": "A",
        "is_incomplete": False,
        "weeks": {"1": {}},
        "source_checked_at": (now - timedelta(days=age)).isoformat()
        if age is not None
        else None,
    }
    result = last_good_group(candidate, old, now)
    assert bool(result.get("is_stale_fallback")) == used
    assert old["group_id"] == "old"
    assert not last_good_group({**candidate, "group_name": "B"}, old, now).get(
        "is_stale_fallback"
    )
    assert source_is_recent(old, now) == used


def test_quality_checks_regression_and_absolute_ceiling(tmp_path):
    baseline = tmp_path / "previous"
    site = tmp_path / "site"
    for root, failed in [(baseline, 20), (site, 21)]:
        (root / "api").mkdir(parents=True)
        (root / "api/status.json").write_text(
            json.dumps({"group_expected_count": 100, "group_failed_count": failed})
        )
    check_parse_quality(site, baseline=baseline)
    (site / "api/status.json").write_text(
        json.dumps({"group_expected_count": 100, "group_failed_count": 22})
    )
    with pytest.raises(RuntimeError):
        check_parse_quality(site, baseline=baseline)
    (site / "api/status.json").write_text(
        json.dumps({"group_expected_count": 100, "group_failed_count": 26})
    )
    with pytest.raises(RuntimeError):
        check_parse_quality(site)


def test_code_publication_reuses_old_api_without_faking_freshness(tmp_path):
    site = tmp_path / "site"
    baseline = tmp_path / "old"
    for root in (site, baseline):
        (root / "api").mkdir(parents=True)
    old = {
        "generated_at": "2026-10-01T00:00:00Z",
        "group_failed_count": 121,
        "build_id": "old",
        "code_revision": "old",
    }
    (baseline / "api/status.json").write_text(json.dumps(old))
    (baseline / "api/test.json").write_bytes(b'{"real old data":true}')
    (site / "api/status.json").write_text(
        json.dumps(
            {
                "build_id": "tested",
                "code_revision": "new",
                "generated_at": "2026-10-17T00:00:00Z",
            }
        )
    )
    with pytest.raises(RuntimeError):
        reuse_api(site, baseline, "wrong")
    reuse_api(site, baseline, "tested")
    result = json.loads((site / "api/status.json").read_text())
    assert (
        result["generated_at"] == old["generated_at"]
        and result["group_failed_count"] == 121
    )
    assert result["build_id"] == "tested" and result["code_revision"] == "new"
    assert (site / "api/test.json").read_bytes() == (
        baseline / "api/test.json"
    ).read_bytes()


def saved_source(root, expected="1146 тпуп", recent=False):
    directory = root / "bakalavriat"
    directory.mkdir()
    (directory / "raspisan.htm").write_text(
        '<table><tr><td>1 курс</td></tr><tr><td><a href="1.htm">'
        + expected
        + "</a></td></tr></table>",
        encoding="cp1251",
    )
    raw = (FIXTURES / "bakalavriat-1.htm").read_bytes()
    (directory / "1.htm").write_bytes(raw)
    checked = datetime.now(UTC) if recent else datetime(2026, 1, 1, tzinfo=UTC)
    (root / "sources.json").write_text(
        json.dumps(
            {
                "bakalavriat/1.htm": {
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "retrieved_at": checked.isoformat(),
                    "last_modified": "Fri, 16 Oct 2026 07:52:00 GMT",
                    "etag": "old-tag",
                }
            }
        )
    )
    return raw


def test_recent_valid_source_is_resumed_without_a_download(tmp_path, monkeypatch):
    raw = saved_source(tmp_path, recent=True)
    network = Mock()
    monkeypatch.setattr(sync_departments, "ROOT", tmp_path)
    monkeypatch.setattr("urllib.request.urlopen", network)
    _, metadata = sync_departments.fetch_page("bakalavriat/1.htm")
    network.assert_not_called()
    assert metadata["reused"]
    assert (tmp_path / "bakalavriat/1.htm").read_bytes() == raw


def test_not_modified_keeps_bytes_and_updates_checked_at(tmp_path, monkeypatch):
    raw = saved_source(tmp_path)
    seen = []

    def response(request, timeout):
        seen.append(request)
        raise HTTPError(request.full_url, 304, "Not Modified", {}, None)

    monkeypatch.setattr(sync_departments, "ROOT", tmp_path)
    monkeypatch.setattr("urllib.request.urlopen", response)
    _, metadata = sync_departments.fetch_page("bakalavriat/1.htm")
    assert seen[0].get_header("If-none-match") == "old-tag"
    assert len(seen) == 1 and metadata["bytes"] == len(raw) and metadata["reused"]
    assert (
        datetime.now(UTC) - datetime.fromisoformat(metadata["retrieved_at"])
    ).total_seconds() < 5
    assert (tmp_path / "bakalavriat/1.htm").read_bytes() == raw


def test_fetch_rejects_wrong_group_before_replacing_saved_source(tmp_path, monkeypatch):
    raw = saved_source(tmp_path, expected="Другая группа")

    class Response:
        headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return raw

    monkeypatch.setattr(sync_departments, "ROOT", tmp_path)
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: Response())
    with pytest.raises(ValueError, match="identity"):
        sync_departments.fetch_page("bakalavriat/1.htm")
    assert (tmp_path / "bakalavriat/1.htm").read_bytes() == raw


def test_durable_data_branch_round_trip(tmp_path):
    from scripts.data_branch import restore, save, git

    remote = tmp_path / "remote.git"
    remote.mkdir()
    git(remote, "init", "--bare", "-q")
    sources = tmp_path / "source"
    sources.mkdir()
    (sources / "bytes.htm").write_bytes(b"raw\r\n\xff")
    site = tmp_path / "site"
    (site / "api").mkdir(parents=True)
    (site / "api/status.json").write_text('{"build_id":"checked"}')
    work = tmp_path / "writer"
    work.mkdir()
    git(work, "init", "-q")
    git(work, "config", "core.autocrlf", "false")
    git(work, "remote", "add", "origin", str(remote))
    save(work, site, sources, "revision")
    target = tmp_path / "reader"
    restored = tmp_path / "restored"
    assert restore(target, str(remote), restored)
    assert (restored / "bytes.htm").read_bytes() == b"raw\r\n\xff"
    assert json.loads((target / "api/status.json").read_text())["build_id"] == "checked"


def test_partial_group_errors_do_not_block_all_healthy_data(tmp_path):
    from scripts.check_sync import check_reports

    for name in ("department-sync.json", "group-sync.json"):
        (tmp_path / name).write_text(
            json.dumps({"downloaded": ["valid.htm"], "failed": [{"path": "bad.htm"}]})
        )
    check_reports(tmp_path, allow_partial=True)
    for name in ("department-sync.json", "group-sync.json"):
        (tmp_path / name).write_text(
            json.dumps({"downloaded": [], "failed": [{"path": "bad.htm"}]})
        )
    with pytest.raises(RuntimeError, match="No source"):
        check_reports(tmp_path, allow_partial=True)


def test_bootstrap_reads_one_published_release_and_detects_a_mid_copy_update(
    tmp_path, monkeypatch
):
    from scripts.published_data import bootstrap
    from urllib.parse import urlparse

    values = {
        "api/status.json": {
            "generated_at": "2026-10-17T00:00:00Z",
            "code_revision": "previous",
        }
    }
    for section in ("bakalavriat", "spezialitet", "zo1", "zo2"):
        values["api/groups/" + section + ".json"] = {
            "groups": [{"id": "1", "name": "A"}]
        }
        values["api/schedule/" + section + "/1.json"] = {"is_incomplete": False}
    for section in ("bakalavriat", "spezialitet"):
        values["api/departments/" + section + ".json"] = {"institutes": []}
        values["api/teachers/all/" + section + ".json"] = {"teachers": []}
    for name in ("rooms", "sources", "catalog-status"):
        values["api/" + name + ".json"] = {}

    class Response:
        def __init__(self, value):
            self.value = value

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return json.dumps(self.value).encode()

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: Response(
            values[urlparse(request.full_url).path.removeprefix("/site/")]
        ),
    )
    bootstrap(tmp_path / "valid", "https://test.invalid/site/")
    assert (
        json.loads((tmp_path / "valid/api/status.json").read_text())[
            "group_expected_count"
        ]
        == 4
    )
    calls = 0

    def changing(request, timeout):
        nonlocal calls
        path = urlparse(request.full_url).path.removeprefix("/site/")
        if path == "api/status.json":
            calls += 1
            return Response({**values[path], "code_revision": str(calls)})
        return Response(values[path])

    monkeypatch.setattr("urllib.request.urlopen", changing)
    with pytest.raises(RuntimeError, match="changed during bootstrap"):
        bootstrap(tmp_path / "invalid", "https://test.invalid/site/")
    assert not (tmp_path / "invalid/api/status.json").exists()
