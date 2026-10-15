"""Shared room index for the HTTP server and GitHub Pages snapshots."""
import re


def normalize_room(raw):
    return re.sub(r'\s+', ' ', re.sub(r'\s*и/д', '', str(raw or ''), flags=re.I)).strip()


def build_rooms_index(schedules):
    rooms = {}
    for schedule in schedules:
        profile = schedule.get('profile') or {}
        for week, days in (schedule.get('weeks') or {}).items():
            for day, data in days.items():
                for pair in data.get('pairs', []):
                    for lesson in pair.get('lessons', []):
                        room = normalize_room(lesson.get('room'))
                        if not room:
                            continue
                        slots = rooms.setdefault(room, {'room': room, 'slots': {}})['slots']
                        entries = slots.setdefault(f"{week}:{day}:{pair['number']}", [])
                        entry = {key: lesson.get(key, '') for key in ('subject', 'type')}
                        entry.update(pair=pair['number'], start=pair['start'], end=pair['end'],
                                     teacher=lesson.get('teacher') or profile.get('short_name', ''),
                                     groups=lesson.get('groups') or schedule.get('group_name', ''))
                        if entry not in entries:
                            entries.append(entry)
    result = sorted(rooms.values(), key=lambda item: item['room'])
    return {'count': len(result), 'rooms': result, 'coverage': 'known_schedules'}
