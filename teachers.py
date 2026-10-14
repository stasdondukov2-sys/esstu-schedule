"""Recover teacher schedules from parsed group snapshots without inventing lessons."""
from copy import deepcopy
from parser import build_teacher_profile, normalize_teacher_key


def teachers_from_groups(schedules):
    teachers = {}
    for schedule in schedules:
        for week, days in (schedule.get('weeks') or {}).items():
            for day, data in days.items():
                for pair in data.get('pairs', []):
                    for lesson in pair.get('lessons', []):
                        name = lesson.get('teacher')
                        key = normalize_teacher_key(name or '')
                        if not key:
                            continue
                        if key not in teachers:
                            profile = build_teacher_profile(name)
                            teachers[key] = dict(mode='teacher', teacher_key=key, teacher_name=name,
                                                 profile=profile, caf_id=profile['caf_id'], weeks={},
                                                 source='group_schedules', partial=True, merged_sections=[])
                        teacher = teachers[key]
                        section = schedule.get('section', '')
                        if section not in teacher['merged_sections']:
                            teacher['merged_sections'].append(section)
                        day_data = teacher['weeks'].setdefault(week, {}).setdefault(day, {
                            **{k: v for k, v in data.items() if k != 'pairs'}, 'pairs': []})
                        target = next((p for p in day_data['pairs'] if
                                       (p['number'], p['start'], p['end']) ==
                                       (pair['number'], pair['start'], pair['end'])), None)
                        if target is None:
                            target = {k: v for k, v in pair.items() if k != 'lessons'}
                            target.update(lessons=[], is_empty=False)
                            day_data['pairs'].append(target)
                        entry = deepcopy(lesson)
                        entry['groups'] = schedule.get('group_name', schedule.get('group_id', ''))
                        entry['source_section'] = section
                        if entry not in target['lessons']:
                            target['lessons'].append(entry)
    for teacher in teachers.values():
        for days in teacher['weeks'].values():
            for data in days.values():
                data['pairs'].sort(key=lambda p: (p['start'], p['number']))
    return sorted(teachers.values(), key=lambda t: t['teacher_key'])


def departments_from_teachers(teachers):
    departments = {}
    for teacher in teachers:
        profile = teacher.get('profile') or {}
        caf = teacher.get('caf_id')
        if caf:
            departments[caf] = {'caf_id': caf, 'name': profile.get('department', caf)}
    return [{'institute': 'Кафедры из сохранённых данных', 'departments': list(departments.values())}] if departments else []
