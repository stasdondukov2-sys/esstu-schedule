import re
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.build_static_site import (
    build_id,
    source_modified_iso,
    stamp_shell,
    write_api_json,
)

ROOT = Path(__file__).resolve().parents[1]


def test_release_version_is_consistent_and_data_cache_is_stable():
    html = (ROOT / "static/index.html").read_text(encoding="utf-8")
    version = re.search(r'content="([0-9.]+)" name="app-release"', html)[1]
    worker = (ROOT / "static/sw.js").read_text(encoding="utf-8")
    assert 'content="__BUILD_ID__" name="app-version"' in html
    assert "const CACHE_NAME = 'esstu-live-__BUILD_ID__';" in worker
    experience = (ROOT / "static/experience.js").read_text(encoding="utf-8")
    assert f"const APP_VERSION = '{version}';" in experience
    assert "const DATA_CACHE = `${CACHE_PREFIX}data-v2`;" in worker


def test_shell_hash_changes_with_assets_but_not_data_or_time(tmp_path):
    (tmp_path / "index.html").write_text(
        '<meta content="__BUILD_ID__" name="app-version"/>'
    )
    (tmp_path / "sw.js").write_text("const CACHE_NAME = 'esstu-live-__BUILD_ID__';")
    css = tmp_path / "app.css"
    css.write_text("body{color:red}")
    (tmp_path / "api").mkdir()
    api = tmp_path / "api/status.json"
    api.write_text('{"generated_at":"first"}')
    first = stamp_shell(tmp_path)
    assert first in (tmp_path / "sw.js").read_text()
    assert (
        f'content="{first}" name="app-version"' in (tmp_path / "index.html").read_text()
    )
    api.write_text('{"generated_at":"later"}')
    assert build_id(tmp_path) == first
    assert stamp_shell(tmp_path) == first
    css.write_text("body{color:blue}")
    second = stamp_shell(tmp_path)
    assert second != first
    assert second in (tmp_path / "sw.js").read_text()
    (tmp_path / "icon.svg").write_text("<svg/>")
    assert build_id(tmp_path) != second


def test_workflows_pin_runner_and_action_revisions():
    for file in (ROOT / ".github/workflows").glob("*.yml"):
        text = file.read_text(encoding="utf-8")
        assert "ubuntu-latest" not in text
        assert "timeout-minutes:" in text
        assert "node-version: '22'" not in text or "ubuntu-24.04" in text
        for action in re.findall(r"uses: (actions/[^\s]+)", text):
            assert re.fullmatch(r"actions/[a-z-]+@[0-9a-f]{40}", action), action


@pytest.mark.parametrize(
    "worker,html",
    [
        ("const OTHER = 'x';", '<meta content="__BUILD_ID__" name="app-version"/>'),
        ("const CACHE_NAME = 'esstu-live-__BUILD_ID__';", '<meta name="other"/>'),
    ],
)
def test_missing_build_marker_fails_without_partial_writes(tmp_path, worker, html):
    (tmp_path / "sw.js").write_text(worker)
    (tmp_path / "index.html").write_text(html)
    with pytest.raises(RuntimeError, match="exactly one"):
        stamp_shell(tmp_path)
    assert (tmp_path / "sw.js").read_text() == worker
    assert (tmp_path / "index.html").read_text() == html


@pytest.mark.parametrize(
    "value,expected",
    [
        ("Fri, 16 Oct 2026 07:52:00 GMT", "2026-10-16T07:52:00+00:00"),
        ("2026-10-16T15:52:00+08:00", "2026-10-16T07:52:00+00:00"),
        (None, None),
        ("Static synchronization", None),
    ],
)
def test_source_modified_time_is_real_iso_or_unknown(value, expected):
    assert source_modified_iso(value) == expected


def test_builder_can_write_unicode_to_redirected_cp1251_stdout():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from scripts.build_static_site import configure_console; configure_console(); print('🚀 Проверка')",
        ],
        cwd=ROOT,
        env={**os.environ, "PYTHONIOENCODING": "cp1251"},
        capture_output=True,
        check=True,
    )
    assert "🚀 Проверка" in result.stdout.decode("utf-8")


def test_api_json_writer_is_atomic_and_versions_payload(tmp_path):
    import json

    path = tmp_path / "api/test.json"
    write_api_json(path, {"count": 1})
    assert json.loads(path.read_text()) == {"count": 1, "schema_version": 2}
    assert not list(tmp_path.rglob("*.tmp"))


def test_worker_only_changes_hash_and_every_local_asset_is_precached(tmp_path):
    import json
    import shutil
    from bs4 import BeautifulSoup
    from scripts.build_static_site import shell_paths

    shutil.copytree(ROOT / "static", tmp_path, dirs_exist_ok=True)
    (tmp_path / "avatars").mkdir(exist_ok=True)
    (tmp_path / "avatars/test.png").write_bytes(
        (ROOT / "static/icons/app-icon-192.png").read_bytes()
    )
    first = stamp_shell(tmp_path)
    worker = tmp_path / "sw.js"
    worker.write_text(
        worker.read_text(encoding="utf-8") + "\n// worker-only behavior change\n",
        encoding="utf-8",
    )
    second = stamp_shell(tmp_path)
    assert first != second and build_id(tmp_path) == second
    shell = json.loads(
        re.search(r"const SHELL = (\[.*?\]);", worker.read_text(encoding="utf-8"))[1]
    )
    assert "./avatars/test.png" in shell
    assert shell == shell_paths(tmp_path)
    html = BeautifulSoup((tmp_path / "index.html").read_text(encoding="utf-8"), "lxml")
    for tag in html.find_all(["script", "link", "img"]):
        url = tag.get("src") or tag.get("href") or ""
        if url and not url.startswith(("http:", "https:", "data:", "#")):
            assert "./" + url.removeprefix("./") in shell
