"""Recover teacher schedules from parsed group snapshots without inventing lessons."""
from copy import deepcopy
import re
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
                        entry['source_type'] = 'group_derived'
                        entry['source_file'] = lesson.get('source_file') or f"{section}/{schedule.get('group_id', '')}.htm"
                        if entry not in target['lessons']:
                            target['lessons'].append(entry)
    for teacher in teachers.values():
        for days in teacher['weeks'].values():
            for data in days.values():
                data['pairs'].sort(key=lambda p: (p['start'], p['number']))
    return sorted(teachers.values(), key=lambda t: t['teacher_key'])


def combine_teacher_catalog(official, derived):
    """Official schedules win; group data only fills missing lessons."""
    result = {}
    for teacher in [*official, *derived]:
        key = teacher['teacher_key']
        if key not in result:
            result[key] = deepcopy(teacher)
            result[key]['caf_ids'] = [teacher['caf_id']] if teacher.get('caf_id') else []
            continue
        target = result[key]
        target['caf_ids'] = sorted(set(target.get('caf_ids', []) + ([teacher['caf_id']] if teacher.get('caf_id') else [])))
        for week, days in teacher.get('weeks', {}).items():
            target_days = target.setdefault('weeks', {}).setdefault(week, {})
            for day_key, day in days.items():
                if day_key not in target_days:
                    target_days[day_key] = deepcopy(day)
                    continue
                pairs = target_days[day_key]['pairs']
                for pair in day['pairs']:
                    matching = next((p for p in pairs if (p['number'], p['start'], p['end']) ==
                                     (pair['number'], pair['start'], pair['end'])), None)
                    if matching is None:
                        pairs.append(deepcopy(pair))
                        continue
                    for lesson in pair['lessons']:
                        existing = matching['lessons']
                        group_key = lambda value: re.sub(r'\W', '', str(value).lower())
                        if lesson.get('subject') == 'Предмет не указан в источнике' and any(
                            l.get('room') == lesson.get('room') and l.get('subject') != 'Предмет не указан в источнике'
                            and group_key(l.get('groups')) == group_key(lesson.get('groups')) for l in existing):
                            continue
                        if any(l.get('subject') == lesson.get('subject') and l.get('room') == lesson.get('room')
                               and (l.get('source_type') == 'official_caf' or l.get('groups') == lesson.get('groups'))
                               for l in existing):
                            continue
                        existing.append(deepcopy(lesson))
                        matching['is_empty'] = False
        target['merged_sections'] = sorted(set(target.get('merged_sections', [target.get('section', '')]) +
                                               teacher.get('merged_sections', [teacher.get('section', '')])))
    for teacher in result.values():
        for days in teacher['weeks'].values():
            for day in days.values():
                day['pairs'].sort(key=lambda p: (p['start'], p['number']))
    return sorted(result.values(), key=lambda t: t['teacher_key'])


def departments_from_teachers(teachers):
    departments = {}
    for teacher in teachers:
        profile = teacher.get('profile') or {}
        caf = teacher.get('caf_id')
        if caf:
            departments[caf] = {'caf_id': caf, 'name': profile.get('department', caf)}
    return [{'institute': 'Кафедры из сохранённых данных', 'departments': list(departments.values())}] if departments else []
