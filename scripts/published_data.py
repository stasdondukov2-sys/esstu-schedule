"""Bootstrap an immutable API snapshot from the currently published Pages site."""

import json
import urllib.request
import urllib.error
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from esstu_schedule.data.store import write_json_atomic


def read_published_json(request):
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read())
        except (urllib.error.URLError, OSError, ValueError) as error:
            if isinstance(error, urllib.error.HTTPError) and error.code not in (
                408,
                429,
                500,
                502,
                503,
                504,
            ):
                raise
            if attempt == 4:
                raise
            time.sleep(2**attempt)


def bootstrap(directory, base):
    api = Path(directory) / "api"

    def fetch(path):
        request = urllib.request.Request(
            base.rstrip("/") + "/" + path,
            headers={"Cache-Control": "no-cache", "User-Agent": "ESSTU-Schedule/2.5"},
        )
        return read_published_json(request)

    status = fetch("api/status.json")
    paths = [
        "api/groups/" + section + ".json"
        for section in ("bakalavriat", "spezialitet", "zo1", "zo2")
    ]
    paths += [
        "api/teachers/all/" + section + ".json"
        for section in ("bakalavriat", "spezialitet")
    ]
    paths += [
        "api/departments/" + section + ".json"
        for section in ("bakalavriat", "spezialitet")
    ]
    paths += ["api/rooms.json", "api/sources.json", "api/catalog-status.json"]
    payloads = {}

    def download(path):
        value = fetch(path)
        write_json_atomic(Path(directory) / path, value)
        return path, value

    with ThreadPoolExecutor(max_workers=4) as pool:
        for path, value in pool.map(download, paths):
            payloads[path] = value
        schedules = [
            f"api/schedule/{section}/{group['id']}.json"
            for section in ("bakalavriat", "spezialitet", "zo1", "zo2")
            for group in payloads[f"api/groups/{section}.json"]["groups"]
        ]
        departments = [
            f"api/department/{section}/{department['caf_id']}.json"
            for section in ("bakalavriat", "spezialitet")
            for institute in payloads[f"api/departments/{section}.json"]["institutes"]
            for department in institute["departments"]
        ]
        list(pool.map(download, sorted(set(schedules + departments))))
    after = fetch("api/status.json")
    if any(
        after.get(key) != status.get(key)
        for key in ("generated_at", "sources_sha256", "code_revision")
    ):
        raise RuntimeError(
            "Published data changed during bootstrap; retry using one complete release"
        )
    status.setdefault("group_expected_count", len(schedules))
    status.setdefault(
        "group_failed_count",
        sum(
            json.loads(path.read_text(encoding="utf-8")).get("is_incomplete", False)
            for path in (api / "schedule").glob("*/*.json")
        ),
    )
    status["baseline_origin"] = base
    write_json_atomic(api / "status.json", status)
    print("Bootstrapped published API:", len(schedules), "groups")
