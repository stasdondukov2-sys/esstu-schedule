"""Download only official department pages; retain the last good copy on failure."""

import json
import hashlib
import logging
import re
import urllib.request
import urllib.error
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

from esstu_schedule.data.repository import (
    department_schedules as parse_department_teachers_html,
)
from esstu_schedule.data.repository import group_schedule as parse_group_schedule_html
from esstu_schedule.parser import parse_departments_list_html, parse_groups_list_html
from esstu_schedule.data.repository import group_identity_error
from esstu_schedule.data.store import write_json_atomic

ROOT = Path(__file__).resolve().parents[1] / "demo_data"
SECTIONS = ("bakalavriat", "spezialitet")


def validate_page(relative, raw):
    html = raw.decode("cp1251", errors="replace")
    section, name = relative.split("/")
    if name == "craspisanEdt.htm":
        valid = parse_departments_list_html(html, section)
    elif name == "raspisan.htm":
        valid = parse_groups_list_html(html, section)
    elif re.fullmatch(r"\d+\.htm", name):
        schedule = parse_group_schedule_html(html, name[:-4], section)
        catalog = ROOT / section / "raspisan.htm"
        groups = (
            parse_groups_list_html(catalog.read_bytes().decode("cp1251"), section)
            if catalog.exists()
            else []
        )
        expected = next(
            (group["name"] for group in groups if group["id"] == name[:-4]), None
        )
        if expected is None or group_identity_error(schedule, expected):
            raise ValueError("Group identity does not match the current catalog")
        valid = not schedule.get("is_incomplete") and bool(
            schedule["weeks"]["1"] or schedule["weeks"]["2"]
        )
    else:
        valid = parse_department_teachers_html(html, name[:-4], section)
    if isinstance(valid, list) and any(item.get("is_incomplete") for item in valid):
        valid = False
    if not valid:
        raise ValueError("Page contains no valid schedule data")


def fetch_page(relative):
    target = ROOT / relative
    manifest_path = ROOT / "sources.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.exists()
        else {}
    )
    old = manifest.get(relative, {})
    previous = target.read_bytes() if target.exists() else None
    valid_saved = previous is not None and hashlib.sha256(
        previous
    ).hexdigest() == old.get("sha256")
    failed_before = any(
        relative == row.get("path")
        for report in ROOT.glob("*sync.json")
        for row in json.loads(report.read_text(encoding="utf-8")).get("failed", [])
    )
    if (
        valid_saved
        and not failed_before
        and relative.split("/")[-1] not in ("raspisan.htm", "craspisanEdt.htm")
    ):
        try:
            age = (
                datetime.now(UTC) - datetime.fromisoformat(old["retrieved_at"])
            ).total_seconds()
            if 0 <= age < 25 * 60:
                validate_page(relative, previous)
                return relative, {**old, "reused": True}
        except (KeyError, TypeError, ValueError):
            pass
    headers = {"User-Agent": "ESSTU-Schedule/2.5"}
    if valid_saved:
        if old.get("etag"):
            headers["If-None-Match"] = old["etag"]
        if old.get("last_modified"):
            headers["If-Modified-Since"] = old["last_modified"]
    for attempt in range(3):
        try:
            request = urllib.request.Request(
                "https://portal.esstu.ru/" + relative, headers=headers
            )
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    raw = response.read()
                    modified = response.headers.get("Last-Modified")
                    etag = response.headers.get("ETag")
                    length = response.headers.get("Content-Length")
                    if length and int(length) != len(raw):
                        raise OSError("Truncated HTTP response")
            except urllib.error.HTTPError as error:
                if error.code != 304 or not valid_saved:
                    raise
                raw = previous
                modified = old.get("last_modified")
                etag = old.get("etag")
            validate_page(relative, raw)
            target.parent.mkdir(parents=True, exist_ok=True)
            if raw != previous:
                temporary = target.with_suffix(target.suffix + ".tmp")
                temporary.write_bytes(raw)
                os.replace(temporary, target)
            return relative, {
                "retrieved_at": datetime.now(UTC).isoformat(),
                "last_modified": modified,
                "etag": etag,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
                "reused": raw == previous,
            }
        except (urllib.error.URLError, OSError) as error:
            if isinstance(error, urllib.error.HTTPError) and error.code < 500:
                raise
            if attempt == 2:
                raise
            time.sleep(0.5 * 2**attempt)


def sync():
    manifest_path = ROOT / "sources.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.exists()
        else {}
    )
    targets, failures, successes = [], [], []
    for section in SECTIONS:
        relative = f"{section}/craspisanEdt.htm"
        try:
            path, meta = fetch_page(relative)
            manifest[path] = meta
            write_json_atomic(manifest_path, manifest)
            successes.append(path)
        except Exception as exc:
            logging.getLogger(__name__).exception(
                "Source synchronization failed: %s", relative
            )
            failures.append({"path": relative, "error": str(exc)})
            # A failed live catalog is not a reason to scan every stale page on an unreachable host.
            continue
        index = ROOT / relative
        if index.exists():
            for institute in parse_departments_list_html(
                index.read_bytes().decode("cp1251"), section
            ):
                for department in institute["departments"]:
                    if re.fullmatch(r"Caf\d+", department["caf_id"], re.IGNORECASE):
                        targets.append(f"{section}/{department['caf_id']}.htm")
    with ThreadPoolExecutor(max_workers=4) as pool:
        pending = {pool.submit(fetch_page, path): path for path in sorted(set(targets))}
        for future in as_completed(pending):
            try:
                path, meta = future.result()
                manifest[path] = meta
                write_json_atomic(manifest_path, manifest)
                successes.append(path)
            except Exception as exc:
                logging.getLogger(__name__).exception(
                    "Source synchronization failed: %s", pending[future]
                )
                failures.append({"path": pending[future], "error": str(exc)})
    write_json_atomic(manifest_path, manifest)
    report = {
        "checked_at": datetime.now(UTC).isoformat(),
        "downloaded": successes,
        "failed": failures,
        "department_pages_expected": len(set(targets)),
    }
    write_json_atomic(ROOT / "department-sync.json", report)
    print(f"Official pages downloaded: {len(successes)}; failed: {len(failures)}")
    return report


if __name__ == "__main__":
    sync()
