"""One validated parsing boundary for the dynamic service and static builder."""

from ..parser import parse_department_teachers_html, parse_group_schedule_html
from .models import validate_schedule


def group_schedule(html, group_id="1", section="bakalavriat"):
    return validate_schedule(parse_group_schedule_html(html, group_id, section))


def department_schedules(
    html, caf_id="Caf5", section="bakalavriat", department_name=""
):
    return [
        validate_schedule(schedule)
        for schedule in parse_department_teachers_html(
            html, caf_id, section, department_name
        )
    ]


def group_identity_error(schedule, expected_name):
    from ..parser import normalize_group_name

    actual = schedule.get("group_name", "")
    if (
        not expected_name
        or not any(character.isalnum() for character in expected_name)
        or expected_name == "Магистратура"
    ):
        return "catalog_placeholder"
    if actual == schedule.get("group_id"):
        return "heading_missing"
    if normalize_group_name(actual) != normalize_group_name(expected_name):
        return "group_name_mismatch"
    return None
