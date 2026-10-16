"""Refresh official department and group snapshots without generating test data."""

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime

from esstu_schedule.data.store import write_json_atomic
from esstu_schedule.parser import SECTIONS, parse_groups_list_html
from scripts.sync_departments import ROOT, fetch_page
from scripts.sync_departments import sync as sync_departments


def sync_groups():
    manifest_path = ROOT / "sources.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.exists()
        else {}
    )
    targets, failures, successes = [], [], []
    for section in SECTIONS:
        relative = f"{section}/raspisan.htm"
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
            continue
        index = ROOT / relative
        if index.exists():
            groups = parse_groups_list_html(
                index.read_bytes().decode("cp1251"), section
            )
            targets.extend(
                f"{section}/{g['id']}.htm"
                for g in groups
                if re.fullmatch(r"\d+", str(g["id"]))
            )
    with ThreadPoolExecutor(max_workers=4) as pool:
        pending = {pool.submit(fetch_page, path): path for path in sorted(set(targets))}
        for future in as_completed(pending):
            try:
                path, meta = future.result()
                manifest[path] = meta
                write_json_atomic(manifest_path, manifest)
                successes.append(path)
                if len(successes) % 50 == 0:
                    print(
                        f"Group synchronization progress: {len(successes)} pages downloaded",
                        flush=True,
                    )
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
        "group_pages_expected": len(set(targets)),
    }
    write_json_atomic(ROOT / "group-sync.json", report)
    print(f"Group pages downloaded: {len(successes)}; failed: {len(failures)}")
    return report


def sync_all():
    sync_departments()
    return sync_groups()


if __name__ == "__main__":
    sync_all()
