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

from esstu_schedule.catalog import build_catalog, source_metadata, stamp_schedule
from esstu_schedule.data.repository import (
    group_schedule as parse_group_schedule_html,
    group_identity_error,
)
from esstu_schedule.parser import (
    SECTIONS,
    get_week_num,
    parse_groups_list_html,
    normalize_group_name,
)
from esstu_schedule.rooms import build_rooms_index
from esstu_schedule.teachers import departments_from_teachers, teachers_from_groups

from esstu_schedule.data.diagnostics import (
    parsing_status,
    record_error,
    reset_diagnostics,
)
from esstu_schedule.data.store import write_json_atomic
from esstu_schedule.data.provenance import build_provenance

BASE_DIR = Path(__file__).resolve().parents[1]
DEMO_DIR = BASE_DIR / "demo_data"
STATIC_DIR = BASE_DIR / "static"
DIST_DIR = BASE_DIR / "dist"


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
    worker.write_text(worker_text, encoding="utf-8")
    index.write_text(index_text, encoding="utf-8")
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

    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Copy static assets (index.html, manifest.json, sw.js, icons)
    for item in STATIC_DIR.iterdir():
        if item.is_file():
            shutil.copy2(item, DIST_DIR / item.name)
        elif item.is_dir():
            shutil.copytree(item, DIST_DIR / item.name)
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

    # 3. Parse and save groups list for all sections
    from scripts.publication import previous_groups, last_good_group

    previous = previous_groups(os.environ.get("ESSTU_BASELINE_DIR"))
    group_schedules = []
    group_expected = 0
    group_failures = []
    metadata = source_metadata(DEMO_DIR, with_hashes=True)
    failed_downloads = {
        row["path"]
        for report in DEMO_DIR.glob("*sync.json")
        for row in json.loads(report.read_text(encoding="utf-8")).get("failed", [])
        if "path" in row
    }
    for section in SECTIONS.keys():
        rasp_file = DEMO_DIR / section / "raspisan.htm"
        if not rasp_file.exists():
            record_error(f"{section}/raspisan.htm", "Отсутствует каталог групп")
            continue
        html = rasp_file.read_bytes().decode("cp1251", errors="replace")
        groups = parse_groups_list_html(html, section=section)
        group_expected += len(groups)
        payload = {"section": section, "count": len(groups), "groups": groups}
        write_api_json(api_dir / "groups" / f"{section}.json", payload)
        print(f"✓ Saved {len(groups)} groups for section '{section}'")

        # 4. Parse group schedules
        sec_sched_dir = api_dir / "schedule" / section
        sec_sched_dir.mkdir(parents=True, exist_ok=True)
        count_sched = 0
        for group in groups:
            gid = group["id"]
            htm_file = DEMO_DIR / section / f"{gid}.htm"
            if not htm_file.exists():
                record_error(f"{section}/{gid}.htm", "Отсутствует расписание группы")
                group_failures.append(
                    {"source": f"{section}/{gid}.htm", "reason": "missing_file"}
                )
                missing = {
                    "mode": "student",
                    "group_id": gid,
                    "group_name": group["name"],
                    "section": section,
                    "is_incomplete": True,
                    "parse_errors": ["Отсутствует расписание группы"],
                    "weeks": {"1": {}, "2": {}},
                    "total_lessons": 0,
                }
                sched = last_good_group(
                    missing,
                    previous.get((section, normalize_group_name(group["name"]))),
                    built_at,
                )
                group_schedules.append(sched)
                write_api_json(sec_sched_dir / f"{gid}.json", sched)
            if htm_file.exists():
                try:
                    g_html = htm_file.read_bytes().decode("cp1251", errors="replace")
                    sched = parse_group_schedule_html(
                        g_html, group_id=gid, section=section
                    )
                    identity_error = group_identity_error(sched, group["name"])
                    if identity_error:
                        group_failures.append(
                            {
                                "source": f"{section}/{gid}.htm",
                                "reason": identity_error,
                                "expected_name": group["name"],
                                "parsed_name": sched["group_name"],
                                "bytes": htm_file.stat().st_size,
                                "sha256": metadata.get(f"{section}/{gid}.htm", {}).get(
                                    "sha256"
                                ),
                            }
                        )
                        record_error(
                            f"{section}/{gid}.htm",
                            "Имя группы не совпадает с каталогом",
                        )
                        sched.update(
                            group_name=group["name"],
                            norm_group_name=group["norm_name"],
                            weeks={"1": {}, "2": {}},
                            total_lessons=0,
                            is_incomplete=True,
                            parse_errors=["Имя группы не совпадает с каталогом"],
                        )
                    if sched.get("is_incomplete") and not identity_error:
                        group_failures.append(
                            {
                                "source": f"{section}/{gid}.htm",
                                "reason": "table_structure",
                                "errors": sched.get("parse_errors"),
                                "bytes": htm_file.stat().st_size,
                            }
                        )
                    sched["resolved_group_id"] = gid
                    sched["last_modified"] = source_modified_iso(
                        metadata.get(f"{section}/{gid}.htm", {}).get("last_modified")
                    )
                    sched["week_now"] = now_week
                    sched["week_calculated_at"] = generated_at
                    stamp_schedule(sched, metadata, generated_at)
                    if (
                        os.environ.get("ESSTU_DATA_UPDATE") == "1"
                        and f"{section}/{gid}.htm" in failed_downloads
                    ):
                        sched.update(
                            is_stale_fallback=True,
                            fallback_reason=["Не удалось обновить источник"],
                        )
                    if os.environ.get("ESSTU_DATA_UPDATE") == "1" and not sched.get(
                        "is_incomplete"
                    ):
                        from scripts.publication import source_is_recent

                        if not source_is_recent(sched, built_at):
                            sched.update(
                                is_incomplete=True,
                                parse_errors=[
                                    "Источник старше 7 дней или дата проверки неизвестна"
                                ],
                                weeks={"1": {}, "2": {}},
                                total_lessons=0,
                            )
                            group_failures.append(
                                {
                                    "source": f"{section}/{gid}.htm",
                                    "reason": "source_expired",
                                }
                            )
                    sched = last_good_group(
                        sched,
                        previous.get((section, normalize_group_name(group["name"]))),
                        built_at,
                    )
                    group_schedules.append(sched)
                    write_api_json(sec_sched_dir / f"{gid}.json", sched)
                    count_sched += 1
                except Exception as e:
                    record_error(f"{section}/{gid}.htm", str(e))
                    LOGGER.exception("Group parsing failed: %s/%s", section, gid)
                    group_failures.append(
                        {
                            "source": f"{section}/{gid}.htm",
                            "reason": "parse_exception",
                            "error": str(e),
                        }
                    )
        print(f"✓ Generated {count_sched} schedule JSON files for '{section}'")

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
