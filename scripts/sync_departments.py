"""Download only official department pages; retain the last good copy on failure."""

import json
import hashlib
import logging
import re
import urllib.request
import urllib.error
import os
import time
from datetime import UTC, datetime
from pathlib import Path

from esstu_schedule.data.repository import (
    department_schedules as parse_department_teachers_html,
)
from esstu_schedule.data.repository import group_schedule as parse_group_schedule_html
from esstu_schedule.parser import parse_departments_list_html, parse_groups_list_html
from esstu_schedule.identity import resolve_catalog, issue_text
from scripts.sync_runtime import download_targets, require_time, remaining
from esstu_schedule.data.store import write_json_atomic

ROOT = Path(__file__).resolve().parents[1] / "demo_data"
SECTIONS = ("bakalavriat", "spezialitet")


class SourceDefect(ValueError):
    def __init__(self, issue):
        self.issue = issue
        super().__init__(issue_text(issue))


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
        if not any(group["id"] == name[:-4] for group in groups):
            raise ValueError("Group identity does not match the current catalog")
        _, issues, _ = resolve_catalog(groups, {name[:-4]: schedule})
        if name[:-4] in issues:
            if issues[name[:-4]]["category"] == "source":
                raise SourceDefect(issues[name[:-4]])
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
    require_time()
    target = ROOT / relative
    rejected = ROOT / ".negative" / relative
    rejected_meta = rejected.with_suffix(".json")
    if rejected_meta.exists():
        saved = json.loads(rejected_meta.read_text(encoding="utf-8"))
        if (
            saved.get("catalog_sha256")
            == hashlib.sha256(
                (ROOT / relative.split("/")[0] / "raspisan.htm").read_bytes()
            ).hexdigest()
        ):
            age = (
                datetime.now(UTC) - datetime.fromisoformat(saved["checked_at"])
            ).total_seconds()
            if 0 <= age < 24 * 3600:
                raise SourceDefect(saved["issue"])
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
        require_time()
        try:
            request = urllib.request.Request(
                "https://portal.esstu.ru/" + relative, headers=headers
            )
            try:
                with urllib.request.urlopen(
                    request, timeout=min(10, remaining())
                ) as response:
                    chunks = []
                    while True:
                        require_time()
                        try:
                            chunk = response.read(65536)
                        except TypeError:
                            chunks = [response.read()]
                            break
                        if not chunk:
                            break
                        chunks.append(chunk)
                    raw = b"".join(chunks)
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
            try:
                validate_page(relative, raw)
            except SourceDefect as error:
                rejected.parent.mkdir(parents=True, exist_ok=True)
                rejected.write_bytes(raw)
                write_json_atomic(
                    rejected_meta,
                    {
                        "checked_at": datetime.now(UTC).isoformat(),
                        "issue": error.issue,
                        "sha256": hashlib.sha256(raw).hexdigest(),
                        "etag": etag,
                        "last_modified": modified,
                        "catalog_sha256": hashlib.sha256(
                            (
                                ROOT / relative.split("/")[0] / "raspisan.htm"
                            ).read_bytes()
                        ).hexdigest(),
                    },
                )
                raise
            if rejected_meta.exists():
                rejected_meta.unlink()
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
            time.sleep(min(0.5 * 2**attempt, remaining()))


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
    for relative, result, error in download_targets(targets, fetch_page):
        if error:
            failures.append(
                {
                    "path": relative,
                    "error": str(error),
                    "reason": error.issue["reason"]
                    if isinstance(error, SourceDefect)
                    else "download_failed",
                }
            )
        else:
            path, meta = result
            manifest[path] = meta
            write_json_atomic(manifest_path, manifest)
            successes.append(path)
    write_json_atomic(manifest_path, manifest)
    report = {
        "checked_at": datetime.now(UTC).isoformat(),
        "downloaded": successes,
        "failed": failures,
        "department_pages_expected": len(set(targets)),
        "deadline_reached": remaining() <= 0,
        "deferred": sorted(
            set(targets) - set(successes) - {row["path"] for row in failures}
        ),
    }
    write_json_atomic(ROOT / "department-sync.json", report)
    print(f"Official pages downloaded: {len(successes)}; failed: {len(failures)}")
    return report


if __name__ == "__main__":
    sync()
