"""Recover teacher schedules from parsed group snapshots without inventing lessons."""

import re
from copy import deepcopy

from .parser import build_teacher_profile, normalize_teacher_key


def teachers_from_groups(schedules):
    teachers = {}
    for schedule in schedules:
        if schedule.get("is_incomplete"):
            continue
        for week, days in (schedule.get("weeks") or {}).items():
            for day, data in days.items():
                for pair in data.get("pairs", []):
                    for lesson in pair.get("lessons", []):
                        name = lesson.get("teacher")
                        key = normalize_teacher_key(name or "")
                        if not key:
                            continue
                        if key not in teachers:
                            profile = build_teacher_profile(name)
                            teachers[key] = dict(
                                mode="teacher",
                                teacher_key=key,
                                teacher_name=name,
                                profile=profile,
                                caf_id=profile["caf_id"],
                                weeks={},
                                source="group_schedules",
                                partial=True,
                                merged_sections=[],
                            )
                        teacher = teachers[key]
                        section = schedule.get("section", "")
                        if section not in teacher["merged_sections"]:
                            teacher["merged_sections"].append(section)
                        day_data = (
                            teacher["weeks"]
                            .setdefault(week, {})
                            .setdefault(
                                day,
                                {
                                    **{k: v for k, v in data.items() if k != "pairs"},
                                    "pairs": [],
                                },
                            )
                        )
                        target = next(
                            (
                                p
                                for p in day_data["pairs"]
                                if (p["number"], p["start"], p["end"])
                                == (pair["number"], pair["start"], pair["end"])
                            ),
                            None,
                        )
                        if target is None:
                            target = {k: v for k, v in pair.items() if k != "lessons"}
                            target.update(lessons=[], is_empty=False)
                            day_data["pairs"].append(target)
                        entry = deepcopy(lesson)
                        entry["groups"] = schedule.get(
                            "group_name", schedule.get("group_id", "")
                        )
                        entry["source_section"] = section
                        entry["source_type"] = "group_derived"
                        entry["source_file"] = (
                            lesson.get("source_file")
                            or f"{section}/{schedule.get('group_id', '')}.htm"
                        )
                        if entry not in target["lessons"]:
                            target["lessons"].append(entry)
    for teacher in teachers.values():
        for days in teacher["weeks"].values():
            for data in days.values():
                data["pairs"].sort(key=lambda p: (p["start"], p["number"]))
    return sorted(teachers.values(), key=lambda t: t["teacher_key"])


def combine_teacher_catalog(official, derived):
    """Official schedules win; group data only fills missing lessons."""
    result = {}
    for teacher in [*official, *derived]:
        key = teacher["teacher_key"]
        if key not in result:
            result[key] = deepcopy(teacher)
            result[key]["caf_ids"] = (
                [teacher["caf_id"]] if teacher.get("caf_id") else []
            )
            continue
        target = result[key]
        target["is_incomplete"] = bool(
            target.get("is_incomplete") or teacher.get("is_incomplete")
        )
        target["parse_errors"] = list(
            dict.fromkeys(
                target.get("parse_errors", []) + teacher.get("parse_errors", [])
            )
        )
        target["caf_ids"] = sorted(
            set(
                target.get("caf_ids", [])
                + ([teacher["caf_id"]] if teacher.get("caf_id") else [])
            )
        )
        for week, days in teacher.get("weeks", {}).items():
            target_days = target.setdefault("weeks", {}).setdefault(week, {})
            for day_key, day in days.items():
                if day_key not in target_days:
                    target_days[day_key] = deepcopy(day)
                    continue
                pairs = target_days[day_key]["pairs"]
                for pair in day["pairs"]:
                    matching = next(
                        (
                            p
                            for p in pairs
                            if (p["number"], p["start"], p["end"])
                            == (pair["number"], pair["start"], pair["end"])
                        ),
                        None,
                    )
                    if matching is None:
                        pairs.append(deepcopy(pair))
                        continue
                    for lesson in pair["lessons"]:
                        existing = matching["lessons"]

                        def group_key(value):
                            return re.sub(r"\W", "", str(value).lower())

                        if lesson.get(
                            "subject"
                        ) == "Предмет не указан в источнике" and any(
                            existing_lesson.get("room") == lesson.get("room")
                            and existing_lesson.get("subject")
                            != "Предмет не указан в источнике"
                            and group_key(existing_lesson.get("groups"))
                            == group_key(lesson.get("groups"))
                            for existing_lesson in existing
                        ):
                            continue
                        if any(
                            existing_lesson.get("subject") == lesson.get("subject")
                            and existing_lesson.get("room") == lesson.get("room")
                            and group_key(existing_lesson.get("groups"))
                            == group_key(lesson.get("groups"))
                            and existing_lesson.get("type_code")
                            == lesson.get("type_code")
                            and existing_lesson.get("tag") == lesson.get("tag")
                            for existing_lesson in existing
                        ):
                            continue
                        existing.append(deepcopy(lesson))
                        matching["is_empty"] = False
        target["merged_sections"] = sorted(
            set(
                target.get("merged_sections", [target.get("section", "")])
                + teacher.get("merged_sections", [teacher.get("section", "")])
            )
        )
    for teacher in result.values():
        for days in teacher["weeks"].values():
            for day in days.values():
                day["pairs"].sort(key=lambda p: (p["start"], p["number"]))
    return sorted(result.values(), key=lambda t: t["teacher_key"])


def departments_from_teachers(teachers):
    departments = {}
    for teacher in teachers:
        profile = teacher.get("profile") or {}
        caf = teacher.get("caf_id")
        if caf:
            departments[caf] = {"caf_id": caf, "name": profile.get("department", caf)}
    return (
        [
            {
                "institute": "Кафедры из сохранённых данных",
                "departments": list(departments.values()),
            }
        ]
        if departments
        else []
    )
