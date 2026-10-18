import json
from datetime import UTC, datetime, timedelta

import pytest
from esstu_schedule.identity import resolve_catalog
from esstu_schedule.parser import normalize_group_name
from scripts.group_freshness import group_freshness
from scripts.publication import reuse_api
from scripts.check_sync import check_parse_quality
from scripts.build_static_site import stamp_shell
from scripts import sync_runtime, sync_departments


def group(gid, name):
    return {"id": str(gid), "name": name, "norm_name": normalize_group_name(name)}


@pytest.mark.parametrize(
    "catalog,page,reason,recovered",
    [
        ("...", "ЗМ-314", None, True),
        ("ЗУ-396-1", "ЗУ-395-1", "group_name_mismatch", False),
        ("ЗМ125ппрс", "ЗМ274", "group_name_mismatch", False),
        ("ЗУ-396-1", "....", "source_unfilled", False),
        ("...", "1", "heading_missing", False),
    ],
)
def test_source_identity_categories(catalog, page, reason, recovered):
    groups, issues, repairs = resolve_catalog(
        [group(1, catalog)], {"1": {"group_id": "1", "group_name": page}}
    )
    assert issues.get("1", {}).get("reason") == reason
    assert bool(repairs) == recovered
    assert groups[0]["id"] == "1"
    assert groups[0]["name"] == (page if recovered else catalog)


@pytest.mark.parametrize("expected", ["ЗУ-396-1", "..."])
def test_other_catalog_group_is_never_relabelled(expected):
    groups, issues, repairs = resolve_catalog(
        [group(1, expected), group(2, "ЗУ-395-1")],
        {"1": {"group_id": "1", "group_name": "ЗУ-395-1"}},
    )
    assert issues["1"]["reason"] == "duplicate_page"
    assert issues["1"]["duplicate_of"] == ["2"]
    assert groups[0]["name"] == expected and not repairs


def test_two_placeholder_pages_with_same_name_are_ambiguous():
    _, issues, repairs = resolve_catalog(
        [group(1, "..."), group(2, "....")],
        {str(i): {"group_id": str(i), "group_name": "ЗМ-314"} for i in (1, 2)},
    )
    assert all(item["reason"] == "duplicate_page" for item in issues.values())
    assert not repairs


def test_source_failures_do_not_consume_pipeline_budget(tmp_path):
    (tmp_path / "api").mkdir()
    status = {
        "group_expected_count": 663,
        "group_failed_count": 132,
        "pipeline_failed_count": 0,
        "source_issue_count": 132,
    }
    (tmp_path / "api/status.json").write_text(json.dumps(status))
    check_parse_quality(tmp_path)
    status["pipeline_failed_count"] = 34
    (tmp_path / "api/status.json").write_text(json.dumps(status))
    with pytest.raises(RuntimeError, match="pipeline failures"):
        check_parse_quality(tmp_path)


def test_parser_change_rebuilds_saved_api_without_faking_source_dates(tmp_path):
    previous = tmp_path / "old"
    site = tmp_path / "site"
    for root in (previous, site):
        (root / "api").mkdir(parents=True)
    old = {
        "parser_revision": "old",
        "build_id": "old",
        "generated_at": "2026-10-10T00:00:00Z",
    }
    current = {
        **old,
        "parser_revision": "new",
        "build_id": "tested",
        "generated_at": "2026-10-17T00:00:00Z",
        "source_checked_at_latest": "2026-10-10T00:00:00Z",
        "group_expected_count": 663,
        "pipeline_failed_count": 0,
    }
    for root, status in ((previous, old), (site, current)):
        (root / "api/status.json").write_text(json.dumps(status))
    (site / "api/fixed.json").write_text('{"parser_fix":true}')
    reuse_api(site, previous, "tested")
    result = json.loads((site / "api/status.json").read_text())
    assert result["api_reparsed_from_sources"]
    assert result["source_checked_at_latest"] == current["source_checked_at_latest"]
    assert (site / "api/fixed.json").exists()


def test_freshness_counts_old_and_unknown_groups_even_with_one_fresh_page():
    now = datetime(2026, 10, 17, tzinfo=UTC)
    schedules = [
        {
            "section": "zo1",
            "group_id": str(i),
            "source_checked_at": (now - timedelta(days=i)).isoformat()
            if i < 3
            else None,
        }
        for i in range(4)
    ]
    result = group_freshness(schedules, now)
    assert result["groups_checked_24h"] == 2
    assert result["groups_checked_24h_ratio"] == 0.5
    assert len(result["group_check_dates"]) == 4


def test_bad_parser_candidate_does_not_block_a_code_release(tmp_path):
    previous = tmp_path / "old"
    site = tmp_path / "site"
    for root in (previous, site):
        (root / "api").mkdir(parents=True)
    old = {
        "parser_revision": "old",
        "build_id": "old",
        "generated_at": "2026-10-10T00:00:00Z",
    }
    candidate = {
        **old,
        "parser_revision": "new",
        "build_id": "tested",
        "code_revision": "new-code",
        "generated_at": "2026-10-17T00:00:00Z",
        "group_expected_count": 663,
        "pipeline_failed_count": 100,
    }
    for root, status in ((previous, old), (site, candidate)):
        (root / "api/status.json").write_text(json.dumps(status))
    (previous / "api/good.json").write_bytes(b'{"saved":true}')
    (site / "api/bad.json").write_bytes(b'{"saved":false}')
    reuse_api(site, previous, "tested")
    result = json.loads((site / "api/status.json").read_text())
    assert result["build_id"] == "tested" and result["parser_revision"] == "old"
    assert result["generated_at"] == old["generated_at"]
    assert (
        result["parser_rebuild_error"]
        and result["parser_rebuild_candidate_revision"] == "new"
    )
    assert (site / "api/good.json").read_bytes() == b'{"saved":true}'
    assert not (site / "api/bad.json").exists()


def test_soft_deadline_does_not_schedule_the_rest_of_a_large_catalog(monkeypatch):
    monkeypatch.setattr(sync_runtime, "_deadline", None)
    calls = []

    def fetch(path):
        calls.append(path)
        sync_runtime.set_deadline(0)
        return path

    results = list(sync_runtime.download_targets(map(str, range(100)), fetch))
    assert 1 <= len(calls) <= 4
    assert len(results) == len(calls)
    assert sync_runtime.remaining() == 0


def test_negative_page_is_downloaded_once_per_day_and_keeps_positive_bytes(
    tmp_path, monkeypatch
):
    from tests.test_followup import saved_source

    saved_source(tmp_path, expected="Другая группа")
    target = tmp_path / "bakalavriat/1.htm"
    raw = target.read_bytes()
    calls = []

    class Response:
        headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return raw

    monkeypatch.setattr(sync_departments, "ROOT", tmp_path)
    monkeypatch.setattr(sync_runtime, "_deadline", None)

    def urlopen(*args, **kwargs):
        calls.append(1)
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    for _ in range(2):
        with pytest.raises(sync_departments.SourceDefect):
            sync_departments.fetch_page("bakalavriat/1.htm")
    assert len(calls) == 1
    assert target.read_bytes() == raw
    assert (tmp_path / ".negative/bakalavriat/1.json").exists()


def test_shell_budget_rejects_an_accidentally_bundled_large_file(tmp_path):
    (tmp_path / "index.html").write_text(
        '<meta content="__BUILD_ID__" name="app-version">'
    )
    (tmp_path / "sw.js").write_text("const CACHE_NAME = 'esstu-live-__BUILD_ID__';")
    (tmp_path / "accidental.bin").write_bytes(b"0" * (5 * 1024 * 1024))
    with pytest.raises(RuntimeError, match="5 MiB"):
        stamp_shell(tmp_path)


@pytest.mark.parametrize(
    "gid,expected,reason",
    [
        ("97", "ЗМ-314", None),
        ("3", "ЗУ-436-1", "duplicate_page"),
        ("68", "ЗМ126ппрс", "source_unfilled"),
    ],
)
def test_real_saved_correspondence_pages(gid, expected, reason):
    from pathlib import Path
    from esstu_schedule.parser import parse_groups_list_html
    from esstu_schedule.data.repository import group_schedule

    root = Path(__file__).resolve().parents[1] / "demo_data/zo1"
    groups = parse_groups_list_html(
        (root / "raspisan.htm").read_bytes().decode("cp1251"), "zo1"
    )
    schedule = group_schedule(
        (root / f"{gid}.htm").read_bytes().decode("cp1251"), gid, "zo1"
    )
    resolved, issues, _ = resolve_catalog(groups, {gid: schedule})
    assert next(item["name"] for item in resolved if item["id"] == gid) == expected
    assert issues.get(gid, {}).get("reason") == reason


def test_bootstrap_only_accepts_matching_source_artifact(tmp_path, monkeypatch):
    import hashlib
    from pathlib import Path
    from scripts import source_artifact

    expected = {
        "bakalavriat/1.htm": {
            "sha256": hashlib.sha256(b"exact published bytes").hexdigest(),
            "retrieved_at": "2026-10-16T00:00:00Z",
        }
    }
    artifacts = {
        "artifacts": [
            {
                "id": i,
                "expired": False,
                "workflow_run": {"head_branch": "main", "id": i},
            }
            for i in (1, 2)
        ]
    }
    calls = []

    def run_gh(*args):
        if args[0] == "api":
            return json.dumps(artifacts)
        calls.append(args[2])
        root = Path(args[-1])
        (root / "bakalavriat").mkdir()
        (root / "sources.json").write_text("{}")
        (root / "bakalavriat/1.htm").write_bytes(
            b"wrong bytes" if args[2] == "1" else b"exact published bytes"
        )
        return ""

    monkeypatch.setattr(source_artifact, "run_gh", run_gh)
    target = tmp_path / "sources"
    assert source_artifact.restore_artifact("owner/repo", target, expected)
    assert calls == ["1", "2"]
    assert json.loads((target / "sources.json").read_text()) == expected


@pytest.mark.parametrize("code,retry", [(503, True), (429, True), (404, False)])
def test_published_api_retries_transient_errors_without_hiding_missing_files(
    monkeypatch, code, retry
):
    import urllib.error
    import urllib.request
    from scripts.published_data import read_published_json

    calls = []
    delays = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return b'{"ok":true}'

    def urlopen(request, timeout):
        calls.append(timeout)
        if len(calls) <= 2:
            raise urllib.error.HTTPError(request.full_url, code, "temporary", {}, None)
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    monkeypatch.setattr("scripts.published_data.time.sleep", delays.append)
    request = urllib.request.Request("https://example.invalid/api/status.json")
    if retry:
        assert read_published_json(request) == {"ok": True}
        assert delays == [1, 2] and calls == [20, 20, 20]
    else:
        with pytest.raises(urllib.error.HTTPError):
            read_published_json(request)
        assert len(calls) == 1 and not delays
