"""Identify source defects without treating a different group's timetable as valid."""

from collections import Counter
from copy import deepcopy
from .parser import normalize_group_name

SOURCE_REASONS = frozenset(
    {"catalog_placeholder", "group_name_mismatch", "duplicate_page", "source_unfilled"}
)


def placeholder(name):
    return (
        not name
        or not any(ch.isalnum() for ch in name)
        or name.casefold() in {"магистратура", "бакалавриат", "группа"}
    )


def resolve_catalog(groups, schedules):
    effective = deepcopy(groups)
    issues = {}
    repairs = []
    known = {}
    for group in groups:
        if not placeholder(group["name"]):
            known.setdefault(normalize_group_name(group["name"]), []).append(
                str(group["id"])
            )
    page_counts = Counter(
        normalize_group_name(item.get("group_name", ""))
        for item in schedules.values()
        if not placeholder(item.get("group_name", ""))
    )
    for group in effective:
        gid = str(group["id"])
        schedule = schedules.get(gid)
        if schedule is None:
            continue
        actual = schedule.get("group_name", "")
        key = normalize_group_name(actual)
        reason = None
        conflicts = [other for other in known.get(key, []) if other != gid]
        if actual == schedule.get("group_id"):
            reason = "heading_missing"
        elif placeholder(actual):
            reason = "source_unfilled"
        elif placeholder(group["name"]):
            if conflicts or page_counts[key] > 1:
                reason = "duplicate_page"
            else:
                repairs.append(
                    {"id": gid, "catalog_name": group["name"], "page_name": actual}
                )
                group.update(
                    catalog_name=group["name"],
                    name=actual,
                    norm_name=key,
                    name_origin="page_header",
                )
        elif key != normalize_group_name(group["name"]):
            reason = "duplicate_page" if conflicts else "group_name_mismatch"
        if reason:
            issues[gid] = {
                "reason": reason,
                "category": "source" if reason in SOURCE_REASONS else "pipeline",
                "expected_name": group["name"],
                "parsed_name": actual,
                "duplicate_of": conflicts,
            }
    return effective, issues, repairs


def issue_text(issue):
    reason = issue["reason"]
    name = issue.get("parsed_name", "")
    return {
        "source_unfilled": "Расписание на портале не заполнено.",
        "duplicate_page": f"Источник портала содержит расписание другой группы ({name}).",
        "group_name_mismatch": f"Название на странице портала ({name}) не совпадает с каталогом.",
        "catalog_placeholder": "В каталоге портала не указано название группы.",
        "heading_missing": "Не удалось определить название группы в источнике.",
    }.get(reason, "Не удалось надёжно прочитать расписание.")
