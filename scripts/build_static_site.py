import hashlib
from collections import Counter
import json
import logging
import os
import re
import shutil
import sys
import time
from datetime import UTC, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from esstu_schedule.catalog import build_catalog, source_metadata
from esstu_schedule.parser import (
    get_week_num,
)
from esstu_schedule.rooms import build_rooms_index
from esstu_schedule.teachers import departments_from_teachers, teachers_from_groups

from esstu_schedule.data.diagnostics import (
    parsing_status,
    reset_diagnostics,
)
from esstu_schedule.data.store import write_json_atomic
from esstu_schedule.data.provenance import build_provenance

BASE_DIR = Path(__file__).resolve().parents[1]
DEMO_DIR = Path(os.environ.get("ESSTU_SOURCE_DIR", BASE_DIR / "demo_data"))
STATIC_DIR = BASE_DIR / "static"
DIST_DIR = Path(os.environ.get("ESSTU_DIST_DIR", BASE_DIR / "dist"))


LOGGER = logging.getLogger(__name__)


def shell_paths(dist):
    return [
        "./",
        *[
            "./" + path.relative_to(dist).as_posix()
            for path in sorted(dist.rglob("*"))
            if path.is_file()
            and path.relative_to(dist).parts[0] != "api"
            and path != dist / "sw.js"
        ],
    ]


def build_id(dist: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(dist.rglob("*")):
        relative = path.relative_to(dist)
        if not path.is_file() or relative.parts[0] == "api":
            continue
        content = path.read_bytes()
        if path.suffix in {".html", ".js", ".css", ".json", ".svg", ".txt"}:
            content = content.replace(b"\r\n", b"\n")
        if relative == Path("index.html"):
            content = re.sub(
                rb'content="[^"]+" name="app-version"',
                b'content="__BUILD_ID__" name="app-version"',
                content,
            )
        if relative == Path("sw.js"):
            content = re.sub(
                rb"const CACHE_NAME = '[^']+';",
                b"const CACHE_NAME = 'esstu-live-__BUILD_ID__';",
                content,
            )
            content = re.sub(
                rb"const SHELL = \[.*?\];",
                ("const SHELL = " + json.dumps(shell_paths(dist)) + ";").encode(),
                content,
            )
        digest.update(relative.as_posix().encode())
        digest.update(b"\0")
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()[:16]


def stamp_shell(dist: Path) -> str:
    shell_bytes = sum(
        path.stat().st_size
        for path in dist.rglob("*")
        if path.is_file() and path.relative_to(dist).parts[0] != "api"
    )
    if shell_bytes > 5 * 1024 * 1024:
        raise RuntimeError("Offline shell exceeds the 5 MiB budget")
    identity = build_id(dist)
    worker = dist / "sw.js"
    worker_text, worker_count = re.subn(
        r"const CACHE_NAME = '[^']+';",
        f"const CACHE_NAME = 'esstu-live-{identity}';",
        worker.read_text(encoding="utf-8"),
    )
    index = dist / "index.html"
    index_text, index_count = re.subn(
        r'content="[^"]+" name="app-version"',
        f'content="{identity}" name="app-version"',
        index.read_text(encoding="utf-8"),
    )
    if worker_count != 1 or index_count != 1:
        raise RuntimeError(
            "Expected exactly one CACHE_NAME and app-version marker; shell was not stamped"
        )
    worker_text = re.sub(
        r"const SHELL = \[.*?\];",
        "const SHELL = " + json.dumps(shell_paths(dist)) + ";",
        worker_text,
    )
    worker.write_text(worker_text, encoding="utf-8", newline="\n")
    index.write_text(index_text, encoding="utf-8", newline="\n")
    return identity


def configure_console():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")


def source_modified_iso(value):
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        return parsed.astimezone(UTC).isoformat() if parsed.tzinfo else None
    except (ValueError, TypeError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.astimezone(UTC).isoformat() if parsed.tzinfo else None
        except (ValueError, TypeError):
            return None


def write_api_json(path, payload):
    write_json_atomic(path, {**payload, "schema_version": 2})


def build():
    configure_console()
    reset_diagnostics()
    css_path = STATIC_DIR / "app.css"
    if not css_path.is_file() or not (
        css_path.stat().st_size >= 8000
        and "tailwindcss" in css_path.read_text(encoding="utf-8")
        and "--campus-bg" in css_path.read_text(encoding="utf-8")
    ):
        raise RuntimeError("Сначала соберите полный CSS: npm run build:css")
    print("🚀 Starting static build for GitHub Pages...")
    start_time = time.time()

    if (
        not DIST_DIR.resolve().is_relative_to(BASE_DIR.resolve())
        or DIST_DIR.resolve() == BASE_DIR.resolve()
    ):
        raise RuntimeError("Build output must stay inside the workspace")
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Copy static assets (index.html, manifest.json, sw.js, icons)
    for item in STATIC_DIR.iterdir():
        if item.is_file():
            shutil.copy2(item, DIST_DIR / item.name)
        elif item.is_dir():
            shutil.copytree(item, DIST_DIR / item.name)
    for asset in DIST_DIR.rglob("*"):
        if asset.is_file() and asset.suffix in {
            ".html",
            ".js",
            ".css",
            ".json",
            ".svg",
            ".txt",
        }:
            asset.write_bytes(asset.read_bytes().replace(b"\r\n", b"\n"))
    print("✓ Copied static files to dist/")

    # 2. Create API directory structure
    api_dir = DIST_DIR / "api"
    api_dir.mkdir(parents=True, exist_ok=True)
    (api_dir / "groups").mkdir(parents=True, exist_ok=True)
    (api_dir / "schedule").mkdir(parents=True, exist_ok=True)
    (api_dir / "departments").mkdir(parents=True, exist_ok=True)
    (api_dir / "teachers" / "all").mkdir(parents=True, exist_ok=True)
    (api_dir / "department").mkdir(parents=True, exist_ok=True)

    # Status
    built_at = datetime.now(UTC)
    generated_at = built_at.isoformat()
    now_week = get_week_num(built_at)
    status_payload = {
        "university": "ВСГУТУ",
        "timezone": "Asia/Irkutsk (UTC+8)",
        "server_time_ulan_ude": built_at.astimezone(
            timezone(timedelta(hours=8))
        ).isoformat(),
        "week_calculated_at": generated_at,
        **now_week,
    }

    from scripts.group_build import build_groups

    group_schedules, group_failures, catalog_repairs, group_expected = build_groups(
        DEMO_DIR,
        api_dir,
        metadata=source_metadata(DEMO_DIR, with_hashes=True),
        now=built_at,
        baseline=os.environ.get("ESSTU_BASELINE_DIR"),
        data_update=os.environ.get("ESSTU_DATA_UPDATE") == "1",
    )
    metadata = source_metadata(DEMO_DIR, with_hashes=True)

    catalog, institutes, departments = build_catalog(
        DEMO_DIR, teachers_from_groups(group_schedules)
    )
    for section in ("bakalavriat", "spezialitet"):
        write_api_json(
            api_dir / "teachers" / "all" / f"{section}.json",
            {
                "count": len(catalog),
                "teachers": catalog,
                "generated_at": generated_at,
            },
        )
        write_api_json(
            api_dir / "departments" / f"{section}.json",
            {
                "institutes": institutes[section] or departments_from_teachers(catalog),
                "generated_at": generated_at,
            },
        )
    for section, caf, payload in departments:
        target = api_dir / "department" / section
        target.mkdir(parents=True, exist_ok=True)
        write_api_json(target / f"{caf}.json", payload)
    print(
        f"Official department files: {len(departments)}; combined teachers: {len(catalog)}"
    )

    room_sources = [*group_schedules, *catalog]
    sync_status = (
        json.loads((DEMO_DIR / "department-sync.json").read_text(encoding="utf-8"))
        if (DEMO_DIR / "department-sync.json").exists()
        else {}
    )
    provenance = build_provenance(metadata, BASE_DIR)
    write_json_atomic(api_dir / "sources.json", metadata)
    diagnostics = {**parsing_status(), **provenance}
    diagnostics["incomplete_schedule_count"] = sum(
        bool(item.get("is_incomplete")) for item in [*group_schedules, *catalog]
    )
    from esstu_schedule.identity import SOURCE_REASONS
    from scripts.parser_revision import parser_revision
    from scripts.group_freshness import group_freshness

    diagnostics.update(group_freshness(group_schedules, built_at))
    diagnostics["parser_revision"] = parser_revision()
    diagnostics["catalog_repairs"] = catalog_repairs
    diagnostics["catalog_recovered_count"] = len(catalog_repairs)
    diagnostics["pipeline_failed_count"] = sum(
        row["reason"] not in SOURCE_REASONS for row in group_failures
    )
    diagnostics["source_issue_count"] = sum(
        row["reason"] in SOURCE_REASONS for row in group_failures
    )
    diagnostics["group_failures"] = group_failures
    diagnostics["group_failure_reasons"] = dict(
        Counter(row["reason"] for row in group_failures)
    )
    diagnostics["fallback_group_count"] = sum(
        item.get("source_mode") == "last_good_json" for item in group_schedules
    )
    diagnostics["group_expected_count"] = group_expected
    diagnostics["group_failed_count"] = group_expected - sum(
        not item.get("is_incomplete") for item in group_schedules
    )
    write_api_json(
        api_dir / "catalog-status.json",
        {**sync_status, **diagnostics, "generated_at": generated_at},
    )
    identity = stamp_shell(DIST_DIR)
    write_api_json(
        api_dir / "status.json",
        {
            **status_payload,
            **diagnostics,
            "generated_at": generated_at,
            "build_id": identity,
        },
    )
    rooms_payload = {
        **build_rooms_index(room_sources),
        "generated_at": generated_at,
        "parse_error_count": diagnostics["parse_error_count"],
        "schema_version": 2,
    }
    write_api_json(api_dir / "rooms.json", rooms_payload)
    # Runtime index survives replacing dist/ during the next background build.
    runtime_root = Path(os.environ.get("ESSTU_SNAPSHOT_DIR", BASE_DIR / "cache_store"))
    write_json_atomic(
        Path(os.environ.get("ESSTU_ROOMS_INDEX", runtime_root / "rooms.json")),
        rooms_payload,
    )
    print(
        f"🎉 Build complete in {time.time() - start_time:.2f}s! All output saved to dist/"
    )


if __name__ == "__main__":
    build()
