import json
from datetime import UTC, datetime

from .data.repository import department_schedules as parse_department_teachers_html
from .parser import parse_departments_list_html
from .teachers import combine_teacher_catalog
from .data.provenance import source_manifest
from .data.diagnostics import record_error


def source_metadata(root, with_hashes=False):
    path = root / "sources.json"
    metadata = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return source_manifest(root, metadata) if with_hashes else metadata


def stamp_schedule(schedule, metadata, generated_at):
    source = schedule.get("source_file", "")
    schedule["generated_at"] = generated_at
    schedule["source_checked_at"] = metadata.get(source, {}).get("retrieved_at")
    schedule["source_last_modified"] = metadata.get(source, {}).get("last_modified")
    schedule["source_sha256"] = metadata.get(source, {}).get("sha256")
    schedule["source_mode"] = "saved_snapshot"
    for days in schedule.get("weeks", {}).values():
        for day in days.values():
            for pair in day.get("pairs", []):
                for lesson in pair.get("lessons", []):
                    lesson["source_checked_at"] = metadata.get(
                        lesson.get("source_file"), {}
                    ).get("retrieved_at")
                    lesson["source_sha256"] = metadata.get(
                        lesson.get("source_file"), {}
                    ).get("sha256")
    return schedule


def build_catalog(root, derived):
    metadata = source_metadata(root, with_hashes=True)
    generated_at = datetime.now(UTC).isoformat()
    official, institutes_by_section, departments = [], {}, []
    for section in ("bakalavriat", "spezialitet"):
        index = root / section / "craspisanEdt.htm"
        if not index.exists():
            record_error(f"{section}/craspisanEdt.htm", "Отсутствует каталог кафедр")
        institutes = (
            parse_departments_list_html(index.read_bytes().decode("cp1251"), section)
            if index.exists()
            else []
        )
        institutes_by_section[section] = institutes
        for institute in institutes:
            for department in institute["departments"]:
                caf = department["caf_id"]
                path = root / section / f"{caf}.htm"
                if not path.exists():
                    record_error(
                        f"{section}/{caf}.htm", "Отсутствует расписание кафедры"
                    )
                    continue
                parsed = parse_department_teachers_html(
                    path.read_bytes().decode("cp1251"),
                    caf,
                    section,
                    f"Кафедра «{department['name']}» ({institute['institute']})",
                )
                for teacher in parsed:
                    stamp_schedule(teacher, metadata, generated_at)
                official.extend(parsed)
                departments.append(
                    (
                        section,
                        caf,
                        {
                            "teachers": parsed,
                            "caf_id": caf,
                            "section": section,
                            "source_checked_at": metadata.get(
                                f"{section}/{caf}.htm", {}
                            ).get("retrieved_at"),
                        },
                    )
                )
    catalog = combine_teacher_catalog(official, derived)
    for teacher in catalog:
        stamp_schedule(teacher, metadata, generated_at)
    return catalog, institutes_by_section, departments
