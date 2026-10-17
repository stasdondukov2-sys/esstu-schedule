"""Build independent group outputs, preserving source defects as explicit states."""

import json
import hashlib
from pathlib import Path
from esstu_schedule.data.repository import group_schedule
from esstu_schedule.data.diagnostics import record_error
from esstu_schedule.data.store import write_json_atomic
from esstu_schedule.identity import resolve_catalog, issue_text
from esstu_schedule.parser import (
    SECTIONS,
    parse_groups_list_html,
    normalize_group_name,
    get_week_num,
)
from esstu_schedule.catalog import stamp_schedule
from scripts.publication import previous_groups, last_good_group, source_is_recent


def build_groups(root, api, metadata, now, baseline=None, data_update=False):
    root, api = Path(root), Path(api)
    previous = previous_groups(baseline)
    result = []
    failures = []
    repairs = []
    expected = 0
    failed_downloads = {
        row["path"]
        for report in root.glob("*sync.json")
        for row in json.loads(report.read_text(encoding="utf-8")).get("failed", [])
        if "path" in row
    }
    for section in SECTIONS:
        catalog = root / section / "raspisan.htm"
        if not catalog.exists():
            raise RuntimeError("Missing group catalog: " + section)
        groups = parse_groups_list_html(
            catalog.read_bytes().decode("cp1251", errors="replace"), section
        )
        if not groups:
            raise RuntimeError("Empty group catalog: " + section)
        expected += len(groups)
        parsed = {}
        observed = {}
        pipeline = {}
        for group in groups:
            gid = str(group["id"])
            path = root / section / (gid + ".htm")
            try:
                negative = root / ".negative" / section / (gid + ".htm")
                negative_meta = negative.with_suffix(".json")
                rejected = (
                    json.loads(negative_meta.read_text(encoding="utf-8"))
                    if negative_meta.exists()
                    else {}
                )
                valid_negative = (
                    negative.exists()
                    and rejected.get("catalog_sha256")
                    == hashlib.sha256(catalog.read_bytes()).hexdigest()
                    and rejected.get("sha256")
                    == hashlib.sha256(negative.read_bytes()).hexdigest()
                )
                selected = negative if valid_negative else path
                observed[gid] = (
                    selected,
                    {
                        **metadata.get(f"{section}/{gid}.htm", {}),
                        **(
                            {
                                "retrieved_at": rejected["checked_at"],
                                "sha256": rejected["sha256"],
                                "last_modified": rejected.get("last_modified"),
                            }
                            if valid_negative
                            else {}
                        ),
                    },
                )
                parsed[gid] = group_schedule(
                    selected.read_bytes().decode("cp1251", errors="replace"),
                    gid,
                    section,
                )
            except Exception as error:
                pipeline[gid] = {
                    "reason": "missing_file"
                    if isinstance(error, FileNotFoundError)
                    else "parse_exception",
                    "category": "pipeline",
                    "error": str(error),
                }
        groups, identity_issues, section_repairs = resolve_catalog(groups, parsed)
        repairs.extend({"section": section, **repair} for repair in section_repairs)
        write_json_atomic(
            api / "groups" / f"{section}.json",
            {
                "schema_version": 2,
                "section": section,
                "count": len(groups),
                "groups": groups,
            },
        )
        for group in groups:
            gid = str(group["id"])
            relative = f"{section}/{gid}.htm"
            path = root / relative
            selected, entry = observed.get(gid, (path, metadata.get(relative, {})))
            sched = parsed.get(
                gid,
                {
                    "mode": "student",
                    "source_file": relative,
                    "group_id": gid,
                    "group_name": group["name"],
                    "section": section,
                    "is_incomplete": True,
                    "parse_errors": ["Файл расписания не прочитан."],
                    "weeks": {"1": {}, "2": {}},
                    "bells": [],
                    "total_lessons": 0,
                },
            )
            issue = identity_issues.get(gid) or pipeline.get(gid)
            if not issue and sched.get("is_incomplete"):
                issue = {
                    "reason": "table_structure",
                    "category": "pipeline",
                    "errors": sched.get("parse_errors", []),
                }
            if issue:
                text = (
                    issue_text(issue)
                    if gid in identity_issues
                    else (
                        " ".join(issue.get("errors", []))
                        or "Файл расписания не прочитан."
                    )
                )
                if issue["category"] == "source":
                    text = issue_text(issue)
                sched.update(
                    source_group_name=sched.get("group_name"),
                    group_name=group["name"],
                    norm_group_name=group["norm_name"],
                    weeks={"1": {}, "2": {}},
                    total_lessons=0,
                    is_incomplete=True,
                    parse_errors=[text],
                    incomplete_reason=text,
                    source_issue=issue if issue["category"] == "source" else None,
                )
            sched["resolved_group_id"] = gid
            sched["week_now"] = get_week_num(now)
            sched["week_calculated_at"] = now.isoformat()
            stamp_schedule(sched, {**metadata, relative: entry}, now.isoformat())
            from scripts.build_static_site import source_modified_iso

            sched["last_modified"] = source_modified_iso(entry.get("last_modified"))
            if data_update and relative in failed_downloads:
                sched.update(
                    is_stale_fallback=True,
                    fallback_reason=["Не удалось обновить источник"],
                )
            if (
                data_update
                and not sched.get("is_incomplete")
                and not source_is_recent(sched, now)
            ):
                issue = {"reason": "source_expired", "category": "pipeline"}
                sched.update(
                    is_incomplete=True,
                    parse_errors=[
                        "Источник старше 7 дней или дата проверки неизвестна"
                    ],
                    incomplete_reason="Источник старше 7 дней или дата проверки неизвестна",
                    weeks={"1": {}, "2": {}},
                    total_lessons=0,
                )
            if issue:
                failures.append(
                    {
                        "source": relative,
                        **issue,
                        "bytes": selected.stat().st_size if selected.exists() else 0,
                        "sha256": entry.get("sha256"),
                    }
                )
                if issue["category"] == "pipeline":
                    record_error(relative, issue["reason"])
            sched = last_good_group(
                sched, previous.get((section, normalize_group_name(group["name"]))), now
            )
            write_json_atomic(
                api / "schedule" / section / (gid + ".json"),
                {**sched, "schema_version": 2},
            )
            result.append(sched)
        print(f"Groups {section}: {len(groups)}")
    return result, failures, repairs, expected
