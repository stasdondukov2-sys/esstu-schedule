import json
import logging
import os
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path

from esstu_schedule.catalog import build_catalog, source_metadata, stamp_schedule
from esstu_schedule.data.repository import group_schedule as parse_group_schedule_html
from esstu_schedule.parser import (
    SECTIONS,
    get_week_num,
    normalize_group_name,
    parse_groups_list_html,
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


def build():
    reset_diagnostics()
    css_path = STATIC_DIR / "app.css"
    if not css_path.is_file() or not all(
        selector in css_path.read_text(encoding="utf-8")
        for selector in (".flex", ".bg-teal-600", ".rounded-xl")
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
    worker_file = DIST_DIR / "sw.js"
    worker_file.write_text(
        worker_file.read_text(encoding="utf-8").replace(
            "esstu-live-v2.5.0", f"esstu-live-v2.5.0-{int(start_time)}"
        ),
        encoding="utf-8",
    )

    # 2. Create API directory structure
    api_dir = DIST_DIR / "api"
    api_dir.mkdir(parents=True, exist_ok=True)
    (api_dir / "groups").mkdir(parents=True, exist_ok=True)
    (api_dir / "schedule").mkdir(parents=True, exist_ok=True)
    (api_dir / "departments").mkdir(parents=True, exist_ok=True)
    (api_dir / "teachers" / "all").mkdir(parents=True, exist_ok=True)
    (api_dir / "department").mkdir(parents=True, exist_ok=True)

    # Status
    now_week = get_week_num()
    status_payload = {
        "university": "ВСГУТУ",
        "timezone": "Asia/Irkutsk (UTC+8)",
        "server_time_ulan_ude": "Live CDN",
        **now_week,
    }
    (api_dir / "status.json").write_text(
        json.dumps(status_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 3. Parse and save groups list for all sections
    group_schedules = []
    metadata = source_metadata(DEMO_DIR, with_hashes=True)
    generated_at = datetime.now(UTC).isoformat()
    for section in SECTIONS.keys():
        rasp_file = DEMO_DIR / section / "raspisan.htm"
        if not rasp_file.exists():
            record_error(f"{section}/raspisan.htm", "Отсутствует каталог групп")
            continue
        html = rasp_file.read_bytes().decode("cp1251", errors="replace")
        groups = parse_groups_list_html(html, section=section)
        payload = {"section": section, "count": len(groups), "groups": groups}
        (api_dir / "groups" / f"{section}.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
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
            if htm_file.exists():
                try:
                    g_html = htm_file.read_bytes().decode("cp1251", errors="replace")
                    sched = parse_group_schedule_html(
                        g_html, group_id=gid, section=section
                    )
                    if normalize_group_name(
                        sched["group_name"]
                    ) != normalize_group_name(group["name"]):
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
                    sched["resolved_group_id"] = gid
                    sched["last_modified"] = "Статическая синхронизация ВСГУТУ"
                    sched["week_now"] = now_week
                    stamp_schedule(sched, metadata, generated_at)
                    group_schedules.append(sched)
                    (sec_sched_dir / f"{gid}.json").write_text(
                        json.dumps(sched, ensure_ascii=False), encoding="utf-8"
                    )
                    count_sched += 1
                except Exception as e:
                    record_error(f"{section}/{gid}.htm", str(e))
                    LOGGER.exception("Group parsing failed: %s/%s", section, gid)
        print(f"✓ Generated {count_sched} schedule JSON files for '{section}'")

    catalog, institutes, departments = build_catalog(
        DEMO_DIR, teachers_from_groups(group_schedules)
    )
    for section in ("bakalavriat", "spezialitet"):
        (api_dir / "teachers" / "all" / f"{section}.json").write_text(
            json.dumps(
                {
                    "count": len(catalog),
                    "teachers": catalog,
                    "generated_at": generated_at,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (api_dir / "departments" / f"{section}.json").write_text(
            json.dumps(
                {
                    "institutes": institutes[section]
                    or departments_from_teachers(catalog),
                    "generated_at": generated_at,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    for section, caf, payload in departments:
        target = api_dir / "department" / section
        target.mkdir(parents=True, exist_ok=True)
        (target / f"{caf}.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
    print(
        f"Official department files: {len(departments)}; combined teachers: {len(catalog)}"
    )

    room_sources = []
    for file in (api_dir / "schedule").rglob("*.json"):
        room_sources.append(json.loads(file.read_text(encoding="utf-8")))
    for file in (api_dir / "teachers" / "all").glob("*.json"):
        room_sources.extend(
            json.loads(file.read_text(encoding="utf-8")).get("teachers", [])
        )
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
    write_json_atomic(
        api_dir / "catalog-status.json",
        {**sync_status, **diagnostics, "generated_at": generated_at},
    )
    write_json_atomic(
        api_dir / "status.json",
        {**status_payload, **diagnostics, "generated_at": generated_at},
    )
    rooms_payload = {
        **build_rooms_index(room_sources),
        "generated_at": generated_at,
        "parse_error_count": diagnostics["parse_error_count"],
    }
    write_json_atomic(api_dir / "rooms.json", rooms_payload)
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
