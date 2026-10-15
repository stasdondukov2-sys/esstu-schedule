"""One validated parsing boundary for the dynamic service and static builder."""
from ..parser import parse_group_schedule_html, parse_department_teachers_html
from .models import validate_schedule


def group_schedule(html, group_id='1', section='bakalavriat'):
    return validate_schedule(parse_group_schedule_html(html, group_id, section))


def department_schedules(html, caf_id='Caf5', section='bakalavriat', department_name=''):
    return [validate_schedule(schedule) for schedule in
            parse_department_teachers_html(html, caf_id, section, department_name)]
