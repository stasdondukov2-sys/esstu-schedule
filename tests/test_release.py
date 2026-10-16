import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_release_version_is_consistent_and_data_cache_is_stable():
    html = (ROOT / "static/index.html").read_text(encoding="utf-8")
    version = re.search(r'content="([0-9.]+)" name="app-version"', html)[1]
    worker = (ROOT / "static/sw.js").read_text(encoding="utf-8")
    builder = (ROOT / "scripts/build_static_site.py").read_text(encoding="utf-8")
    assert f"const CACHE_NAME = 'esstu-live-v{version}';" in worker
    assert f"esstu-live-v{version}" in builder
    experience = (ROOT / "static/experience.js").read_text(encoding="utf-8")
    assert f"const APP_VERSION = '{version}';" in experience
    assert "const DATA_CACHE = `${CACHE_PREFIX}data-v1`;" in worker


def test_workflows_pin_runner_and_action_revisions():
    for file in (ROOT / ".github/workflows").glob("*.yml"):
        text = file.read_text(encoding="utf-8")
        assert "ubuntu-latest" not in text
        assert "node-version: '22'" not in text or "ubuntu-24.04" in text
        for action in re.findall(r"uses: (actions/[^\s]+)", text):
            assert re.fullmatch(r"actions/[a-z-]+@[0-9a-f]{40}", action), action
