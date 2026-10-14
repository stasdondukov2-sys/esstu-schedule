import json
import shutil
import time
from pathlib import Path
from parser import (
    SECTIONS,
    get_week_num,
    parse_groups_list_html,
    parse_group_schedule_html,
    parse_departments_list_html,
    parse_department_teachers_html,
    merge_teacher_schedules,
    normalize_group_name,
)

BASE_DIR = Path(__file__).parent
DEMO_DIR = BASE_DIR / "demo_data"
STATIC_DIR = BASE_DIR / "static"
DIST_DIR = BASE_DIR / "dist"

def build():
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
    now_week = get_week_num()
    status_payload = {
        "university": "ВСГУТУ",
        "timezone": "Asia/Irkutsk (UTC+8)",
        "server_time_ulan_ude": "Live CDN",
        **now_week
    }
    (api_dir / "status.json").write_text(json.dumps(status_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # 3. Parse and save groups list for all sections
    for section in SECTIONS.keys():
        rasp_file = DEMO_DIR / section / "raspisan.htm"
        if not rasp_file.exists():
            continue
        html = rasp_file.read_bytes().decode("cp1251", errors="replace")
        groups = parse_groups_list_html(html, section=section)
        payload = {"section": section, "count": len(groups), "groups": groups}
        (api_dir / "groups" / f"{section}.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        print(f"✓ Saved {len(groups)} groups for section '{section}'")

        # 4. Parse group schedules
        sec_sched_dir = api_dir / "schedule" / section
        sec_sched_dir.mkdir(parents=True, exist_ok=True)
        count_sched = 0
        for group in groups:
            gid = group["id"]
            htm_file = DEMO_DIR / section / f"{gid}.htm"
            if htm_file.exists():
                try:
                    g_html = htm_file.read_bytes().decode("cp1251", errors="replace")
                    sched = parse_group_schedule_html(g_html, group_id=gid, section=section)
                    sched["resolved_group_id"] = gid
                    sched["last_modified"] = "Статическая синхронизация ВСГУТУ"
                    sched["week_now"] = now_week
                    (sec_sched_dir / f"{gid}.json").write_text(json.dumps(sched, ensure_ascii=False), encoding="utf-8")
                    count_sched += 1
                except Exception as e:
                    pass
        print(f"✓ Generated {count_sched} schedule JSON files for '{section}'")

    # 5. Departments and Teachers for bakalavriat and spezialitet
    for section in ("bakalavriat", "spezialitet"):
        crasp_file = DEMO_DIR / section / "craspisanEdt.htm"
        if not crasp_file.exists():
            continue
        html = crasp_file.read_bytes().decode("cp1251", errors="replace")
        institutes = parse_departments_list_html(html, section=section)
        dept_payload = {"section": section, "last_modified": "Синхронизировано", "institutes": institutes}
        (api_dir / "departments" / f"{section}.json").write_text(json.dumps(dept_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        sec_dept_dir = api_dir / "department" / section
        sec_dept_dir.mkdir(parents=True, exist_ok=True)

        all_teachers = []
        seen = set()

        for inst in institutes:
            for dept in inst.get("departments", []):
                caf_id = dept["caf_id"].replace(".htm", "")
                dept_name = f"Кафедра «{dept['name']}» ({inst['institute']})"
                caf_file = DEMO_DIR / section / f"{caf_id}.htm"
                if caf_file.exists():
                    try:
                        caf_html = caf_file.read_bytes().decode("cp1251", errors="replace")
                        teachers = parse_department_teachers_html(caf_html, caf_id=caf_id, section=section, department_name=dept_name)
                        
                        # Merge with other section if exists
                        other_sec = "spezialitet" if section == "bakalavriat" else "bakalavriat"
                        other_file = DEMO_DIR / other_sec / f"{caf_id}.htm"
                        if other_file.exists():
                            try:
                                o_html = other_file.read_bytes().decode("cp1251", errors="replace")
                                o_map = {t["teacher_key"]: t for t in parse_department_teachers_html(o_html, caf_id=caf_id, section=other_sec, department_name=dept_name)}
                                teachers = [merge_teacher_schedules(t, o_map.get(t["teacher_key"])) for t in teachers]
                            except Exception:
                                pass
                        
                        caf_payload = {
                            "caf_id": caf_id,
                            "department_name": dept_name,
                            "section": section,
                            "last_modified": "Синхронизировано",
                            "teachers": teachers
                        }
                        (sec_dept_dir / f"{caf_id}.json").write_text(json.dumps(caf_payload, ensure_ascii=False), encoding="utf-8")

                        for t in teachers:
                            if t["teacher_key"] not in seen:
                                seen.add(t["teacher_key"])
                                all_teachers.append(t)
                    except Exception:
                        pass
        
        all_teach_payload = {"count": len(all_teachers), "teachers": all_teachers}
        (api_dir / "teachers" / "all" / f"{section}.json").write_text(json.dumps(all_teach_payload, ensure_ascii=False), encoding="utf-8")
        print(f"✓ Generated {len(all_teachers)} teachers for '{section}'")

    print(f"🎉 Build complete in {time.time()-start_time:.2f}s! All output saved to dist/")

if __name__ == "__main__":
    build()
