import json
import re
import logging
from copy import deepcopy
from functools import lru_cache
from threading import RLock
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from bs4 import BeautifulSoup

ESSTU_BASE_URL = "https://portal.esstu.ru"

SECTIONS = {
    "bakalavriat": "Бакалавриат, специалитет",
    "spezialitet": "Магистратура, колледж, ДОУ",
    "zo1": "Заочное 1",
    "zo2": "Заочное 2",
}

DAYS_MAP = {
    "пнд": ("monday", "Понедельник", "Пн", 0),
    "пон": ("monday", "Понедельник", "Пн", 0),
    "втр": ("tuesday", "Вторник", "Вт", 1),
    "вто": ("tuesday", "Вторник", "Вт", 1),
    "срд": ("wednesday", "Среда", "Ср", 2),
    "сре": ("wednesday", "Среда", "Ср", 2),
    "чтв": ("thursday", "Четверг", "Чт", 3),
    "чет": ("thursday", "Четверг", "Чт", 3),
    "птн": ("friday", "Пятница", "Пт", 4),
    "пят": ("friday", "Пятница", "Пт", 4),
    "сбт": ("saturday", "Суббота", "Сб", 5),
    "суб": ("saturday", "Суббота", "Сб", 5),
}

INDEX_TO_DAY = [
    ("monday", "Понедельник", "Пн", 0),
    ("tuesday", "Вторник", "Вт", 1),
    ("wednesday", "Среда", "Ср", 2),
    ("thursday", "Четверг", "Чт", 3),
    ("friday", "Пятница", "Пт", 4),
    ("saturday", "Суббота", "Сб", 5),
]

RU_MONTHS = {
    "янв": 1, "фев": 2, "мар": 3, "апр": 4, "май": 5, "мая": 5,
    "июн": 6, "июл": 7, "авг": 8, "сен": 9, "окт": 10, "ноя": 11, "дек": 12,
}

# Поддержка до 7 пар (для заочников zo1 / zo2)
DEFAULT_BELLS = [
    {"number": 1, "label": "1-я", "start": "09:00", "end": "10:35"},
    {"number": 2, "label": "2-я", "start": "10:45", "end": "12:20"},
    {"number": 3, "label": "3-я", "start": "13:00", "end": "14:35"},
    {"number": 4, "label": "4-я", "start": "14:45", "end": "16:20"},
    {"number": 5, "label": "5-я", "start": "16:25", "end": "18:00"},
    {"number": 6, "label": "6-я", "start": "18:05", "end": "19:40"},
    {"number": 7, "label": "7-я", "start": "19:45", "end": "21:20"},
]

TEACHERS_META_PATH = Path(__file__).parent / "teachers_meta.json"
LOGGER = logging.getLogger(__name__)
META_LOCK = RLock()
AVATAR_ROOT = Path(__file__).parent / 'static'


def local_teacher_photo(value: str) -> str:
    if not isinstance(value, str) or len(value) > 128 or not re.fullmatch(r'avatars/[A-Za-z0-9_-]+\.(?:png|jpe?g|webp)', value, re.I):
        return ''
    path = (AVATAR_ROOT / value).resolve()
    return value if path.is_relative_to(AVATAR_ROOT.resolve()) and path.is_file() else ''


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def normalize_group_name(name: str) -> str:
    """Нормализует название группы для защиты от плавающих URL (Issue #4: 78.htm -> 80.htm)."""
    s = clean_text(name).lower().replace("ё", "е").rstrip(".")
    return re.sub(r"\s+", " ", s)


@lru_cache(maxsize=4)
def _read_teachers_meta(path: str, modified_ns: int, size: int):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def load_teachers_meta() -> Dict[str, Dict[str, Any]]:
    try:
        stat = TEACHERS_META_PATH.stat()
        return deepcopy(_read_teachers_meta(str(TEACHERS_META_PATH), stat.st_mtime_ns, stat.st_size))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        LOGGER.warning('Could not read teacher metadata', exc_info=True)
        return {}


def save_teacher_meta_entry(teacher_key: str, entry: Dict[str, Any]) -> Dict[str, Any]:
    if entry.get('photo') and not local_teacher_photo(entry['photo']):
        raise ValueError('Фото должно быть существующим локальным файлом avatars/*.png, *.jpg или *.webp')
    with META_LOCK:
        meta = load_teachers_meta()
        norm_key = normalize_teacher_key(teacher_key)
        existing = meta.get(norm_key, {})
        existing.update(entry)
        meta[norm_key] = existing
        TEACHERS_META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        _read_teachers_meta.cache_clear()
        return existing


def normalize_teacher_key(raw_name: str) -> str:
    cleaned = clean_text(raw_name).lower().replace("ё", "е")
    m = re.search(r"([а-яa-z\-]+)\s+([а-яa-z])\.\s*([а-яa-z])\.", cleaned)
    if m:
        return f"{m.group(1)} {m.group(2)}.{m.group(3)}."
    return cleaned


def format_teacher_display_name(raw_name: str) -> str:
    cleaned = clean_text(raw_name)
    m = re.search(r"([А-ЯЁа-яё\-]+)\s+([А-ЯЁа-яё])\.\s*([А-ЯЁа-яё])\.", cleaned)
    if m:
        surname = "-".join(p.capitalize() for p in m.group(1).split("-"))
        return f"{surname} {m.group(2).upper()}.{m.group(3).upper()}."
    return cleaned


def build_teacher_profile(raw_name: str, caf_id: str = "", department_name: str = "") -> Dict[str, Any]:
    norm_key = normalize_teacher_key(raw_name)
    display_name = format_teacher_display_name(raw_name)
    meta = load_teachers_meta().get(norm_key, {})
    parts = display_name.replace(".", " ").split()
    initials = "".join(p[0].upper() for p in parts[:2]) if parts else "П"
    return {
        "key": norm_key,
        "raw_name": clean_text(raw_name),
        "short_name": meta.get("short_name") or display_name,
        "full_name": meta.get("full_name") or display_name,
        "degree": meta.get("degree") or "Преподаватель ВСГУТУ",
        "department": meta.get("department") or department_name or "Кафедра ВСГУТУ",
        "caf_id": caf_id or meta.get("caf_id") or "",
        "building": meta.get("building") or "",
        "photo": local_teacher_photo(meta.get('photo')),
        "initials": initials,
    }


def get_reference_date(target_dt: datetime) -> datetime:
    year = target_dt.year
    ref_year = year - 1 if target_dt.month <= 7 else year
    first_sept = datetime(ref_year, 9, 1, tzinfo=target_dt.tzinfo)
    wd = first_sept.weekday()
    if wd == 0:
        return datetime(ref_year, 9, 1, tzinfo=target_dt.tzinfo)
    elif wd in (1, 2, 3, 4):
        return datetime(ref_year, 8, 32 - wd, tzinfo=target_dt.tzinfo)
    elif wd == 5:
        return datetime(ref_year, 9, 3, tzinfo=target_dt.tzinfo)
    return datetime(ref_year, 9, 2, tzinfo=target_dt.tzinfo)


def get_week_num(target_dt: Optional[datetime] = None) -> Dict[str, Any]:
    ulan_ude_tz = timezone(timedelta(hours=8))
    if target_dt is None:
        target_dt = datetime.now(ulan_ude_tz)
    elif target_dt.tzinfo is None:
        target_dt = target_dt.replace(tzinfo=ulan_ude_tz)
    ref_date = get_reference_date(target_dt)
    diff_weeks = (target_dt - ref_date).total_seconds() / (60 * 60 * 24 * 7)
    is_odd = (int(diff_weeks) % 2 == 0) if diff_weeks >= 0 else (int(diff_weeks + 1 / 7) % 2 != 0)
    return {
        "week_number": 1 if is_odd else 2,
        "week_title": "I неделя" if is_odd else "II неделя",
        "reference_date": ref_date.strftime("%Y-%m-%d"),
    }


def extract_tags(text: str) -> List[str]:
    tags = []
    low = text.lower()
    for lang in ("англ", "франц", "нем", "кит"):
        if lang in low:
            tags.append(lang)
    for subgroup in ("1", "2"):
        if re.search(r"(?<!\d)" + subgroup + r"\s*(?:[-–]\s*[яй]\s*)?(?:п\s*/?\s*гр?\.?|подгрупп[а-яё]*|подгр\.?)(?![а-яё\d])", low):
            tags.append(f"{subgroup} п/г")
    return tags


def parse_single_lesson_chunk(chunk: str) -> Dict[str, Any]:
    raw = clean_text(chunk)
    lesson_type, type_code, rest = "Занятие", "other", raw
    type_match = re.match(r"^(лек\.|пр\.|лаб\.|сем\.|конс\.|экз\.|зач\.)\s*(.*)$", raw, flags=re.I)
    if type_match:
        prefix = type_match.group(1).lower()
        rest = type_match.group(2).strip()
        if prefix.startswith("лек"):
            lesson_type, type_code = "Лекция", "lecture"
        elif prefix.startswith("пр") or prefix.startswith("сем"):
            lesson_type, type_code = "Практика", "practice"
        elif prefix.startswith("лаб"):
            lesson_type, type_code = "Лабораторная", "lab"
        elif prefix.startswith("экз"):
            lesson_type, type_code = "Экзамен", "exam"
        elif prefix.startswith("зач"):
            lesson_type, type_code = "Зачёт", "test"
        elif prefix.startswith("конс"):
            lesson_type, type_code = "Консультация", "consultation"
    elif "физическая культура" in raw.lower() or "фкс" in raw.lower():
        lesson_type, type_code = "Физкультура", "sport"

    room = ""
    room_match = re.search(r"\bа\.?\s*([0-9А-Яа-яA-Za-z\-/]+(?:\s+и/д)?)\s*$", rest)
    if room_match:
        room = room_match.group(1).strip()
        rest = rest[: room_match.start()].strip()

    teacher, teacher_key, teacher_profile = "", "", None
    teacher_match = re.search(r"([А-ЯЁ][А-ЯЁа-яё\-]+\s+[А-ЯЁ]\.\s*[А-ЯЁ]\.(?:[А-ЯЁа-яё\.]+)?)\s*$", rest)
    if teacher_match:
        raw_t = teacher_match.group(1).strip()
        teacher = format_teacher_display_name(raw_t)
        teacher_key = normalize_teacher_key(raw_t)
        teacher_profile = build_teacher_profile(raw_t)
        rest = rest[: teacher_match.start()].strip()

    tags = extract_tags(raw)
    ambiguous = len(re.findall(r'\bа\.\s*\d', raw, re.I)) > 1 or room.endswith(('-', '/'))
    if ambiguous:
        # Keep the original cell for inspection instead of assigning one teacher/room to several lessons.
        rest, lesson_type, type_code = 'Несколько занятий — сверьте с источником', 'Требуется сверка', 'other'
        room, teacher, teacher_key, teacher_profile = '', '', '', None
    return {
        "raw": raw,
        "type": lesson_type,
        "type_code": type_code,
        "subject": rest if rest else raw,
        "teacher": teacher,
        "teacher_key": teacher_key,
        "teacher_photo": teacher_profile["photo"] if teacher_profile else "",
        "teacher_caf_id": teacher_profile["caf_id"] if teacher_profile else "",
        "room": room,
        "tag": ", ".join(tags),
        "tags": tags,
        "groups": "",
        "parse_warning": 'В ячейке несколько аудиторий или неполный номер. Проверьте исходное расписание.' if ambiguous else '',
    }


def parse_cell_lessons(cell_text: str) -> List[Dict[str, Any]]:
    text = clean_text(cell_text)
    if not text or text in ("_", "-", "—"):
        return []
    parts = re.split(r"(?=(?:^|\s)(?:лек\.|пр\.|лаб\.|сем\.|экз\.|зач\.|конс\.))", text, flags=re.I)
    parts = [clean_text(p) for p in parts if clean_text(p) and clean_text(p) != "_"]
    expanded_parts: List[str] = []
    base_prefix = ""
    for p in parts:
        m_pref = re.match(r"^(лек\.|пр\.|лаб\.|сем\.)\s*([А-ЯЁа-яё\s]+?)(?=\(|[А-ЯЁ]{2,})", p, flags=re.I)
        if m_pref:
            base_prefix = f"{m_pref.group(1)}{m_pref.group(2).strip()} "
        marked = re.sub(
            r"(\bа\.[0-9А-Яа-яA-Za-z\-/]{2,10})\s+(?=(?:лек\.|пр\.|лаб\.|\(|[А-ЯЁ]))",
            r"\1|||SPLIT|||",
            p,
        )
        for sc in marked.split("|||SPLIT|||"):
            sc_clean = clean_text(sc)
            if not sc_clean:
                continue
            if base_prefix and not re.match(r"^(лек\.|пр\.|лаб\.|сем\.)", sc_clean, flags=re.I):
                if sc_clean.startswith("("):
                    sc_clean = base_prefix + sc_clean
            expanded_parts.append(sc_clean)
    final_parts = expanded_parts if expanded_parts else [text]
    return [parse_single_lesson_chunk(p) for p in final_parts]


def parse_teacher_cell_lessons(cell_text: str, teacher_name: str = "", section: str = "bakalavriat") -> List[Dict[str, Any]]:
    text = clean_text(cell_text)
    if not text or text in ("_", "-", "—"):
        return []
    lesson_type, type_code, subject, before_subject, groups_str, room = "Занятие", "other", text, text, "", ""
    type_match = re.search(r"\b(лек\.|пр\.|лаб\.|сем\.|экз\.|зач\.|конс\.)\s*(.+)$", text, flags=re.I)
    if type_match:
        prefix = type_match.group(1).lower()
        subject = clean_text(type_match.group(2))
        before_subject = clean_text(text[: type_match.start()])
        if prefix.startswith("лек"):
            lesson_type, type_code = "Лекция", "lecture"
        elif prefix.startswith("пр") or prefix.startswith("сем"):
            lesson_type, type_code = "Практика", "practice"
        elif prefix.startswith("лаб"):
            lesson_type, type_code = "Лабораторная", "lab"
        elif prefix.startswith("экз"):
            lesson_type, type_code = "Экзамен", "exam"
        elif prefix.startswith("зач"):
            lesson_type, type_code = "Зачёт", "test"
        elif prefix.startswith("конс"):
            lesson_type, type_code = "Консультация", "consultation"
    room_match = re.search(r"\bа\.\s*((?:[0-9][0-9А-Яа-яA-Za-z\-/]*|дист\.*|д\.о\.[/]*)(?:\s+и/д)?)", before_subject, flags=re.I)
    if room_match:
        room = room_match.group(1).strip()
        groups_str = clean_text(before_subject[: room_match.start()])
        if not type_match:
            subject = clean_text(before_subject[room_match.end():]) or 'Предмет не указан в источнике'
    else:
        groups_str = before_subject
    tags = extract_tags(text)
    return [{
        "raw": text,
        "type": lesson_type,
        "type_code": type_code,
        "subject": subject,
        "teacher": format_teacher_display_name(teacher_name) if teacher_name else "",
        "teacher_key": normalize_teacher_key(teacher_name) if teacher_name else "",
        "room": room,
        "groups": groups_str,
        "section": section,
        "section_badge": "Магистратура/Колледж" if section == "spezialitet" else "Бакалавриат",
        "tag": ", ".join(tags),
        "tags": tags,
    }]


def parse_day_or_date_cell(raw_cell_text: str, fallback_row_idx: int) -> Optional[Tuple[str, str, str, int, str]]:
    """Поддержка стандартных дней ('Пнд'..'Сбт') и дат сессии заочников ('15 янв', '16.01')."""
    cleaned = clean_text(raw_cell_text).lower()
    if not cleaned:
        return None
    prefix3 = cleaned[:3]

    m_ru = re.search(r"(\d{1,2})\s*([а-яё]{3,})(?:\s+(\d{4}))?", cleaned)
    if m_ru and m_ru.group(2)[:3] in RU_MONTHS:
        day_num = int(m_ru.group(1))
        mon_num = RU_MONTHS[m_ru.group(2)[:3]]
        year = int(m_ru.group(3)) if m_ru.group(3) else None
        date_label = f"{day_num:02d}.{mon_num:02d}" + (f'.{year:04d}' if year else '')
        # A date without a year does not identify a weekday. Keep it as a dated row.
        try:
            datetime(year or 2000, mon_num, day_num)
        except ValueError:
            return None
        return f'date_{date_label}', date_label, date_label, -1, date_label

    m_num = re.search(r"(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?", cleaned)
    if m_num:
        year = int(m_num.group(3)) if m_num.group(3) else None
        date_label = f"{int(m_num.group(1)):02d}.{int(m_num.group(2)):02d}" + (f'.{year:04d}' if year else '')
        try:
            datetime(year or 2000, int(m_num.group(2)), int(m_num.group(1)))
        except ValueError:
            return None
        return f'date_{date_label}', date_label, date_label, -1, date_label
    if prefix3 in DAYS_MAP:
        day_key, day_title, day_short, day_index = DAYS_MAP[prefix3]
        return day_key, day_title, day_short, day_index, ""
    return None


def parse_groups_list_html(html: str, section: str = "bakalavriat") -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    groups, seen = [], set()
    table = soup.find("table")
    if not table:
        return groups
    rows = table.find_all("tr")
    if not rows:
        return groups
    courses = []
    for td in rows[0].find_all(["td", "th"]):
        m = re.search(r"(\d+)", clean_text(td.get_text()))
        courses.append(int(m.group(1)) if m else len(courses) + 1)
    for tr in rows[1:]:
        for col_idx, td in enumerate(tr.find_all("td")):
            course = courses[col_idx] if col_idx < len(courses) else col_idx + 1
            for a in td.find_all("a"):
                href = (a.get("href") or "").strip()
                name = clean_text(a.get_text())
                if not name or not href or (section, href, name) in seen:
                    continue
                seen.add((section, href, name))
                groups.append({
                    "id": href.replace(".htm", ""),
                    "href": href,
                    "name": name,
                    "norm_name": normalize_group_name(name),
                    "course": course,
                    "section": section,
                    "section_title": SECTIONS.get(section, section),
                })
    return groups


def parse_14row_table(table, is_teacher: bool = False, owner_name: str = "", section: str = "bakalavriat") -> Dict[str, Any]:
    rows = table.find_all("tr") if table else []
    max_pairs = 6
    if len(rows) > 0:
        header_cells = rows[0].find_all(["td", "th"])[1:]
        if len(header_cells) >= 7:
            max_pairs = len(header_cells)
    bells = list(DEFAULT_BELLS[:max_pairs])

    if len(rows) > 1:
        time_cells = rows[1].find_all(["td", "th"])[1:]
        if len(time_cells) > max_pairs:
            max_pairs = len(time_cells)
        parsed_bells = []
        for idx, td in enumerate(time_cells):
            m = re.search(r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})", clean_text(td.get_text()))
            if m:
                s_t = "0" + m.group(1) if len(m.group(1)) == 4 else m.group(1)
                e_t = "0" + m.group(2) if len(m.group(2)) == 4 else m.group(2)
                parsed_bells.append({"number": idx + 1, "label": f"{idx + 1}-я", "start": s_t, "end": e_t})
            elif idx < len(DEFAULT_BELLS):
                parsed_bells.append(DEFAULT_BELLS[idx])
        if parsed_bells:
            bells = parsed_bells

    weeks: Dict[str, Dict[str, Any]] = {"1": {}, "2": {}}
    total_lessons = 0
    day_occurrences = {}
    for row_idx, tr in enumerate(rows[2:]):
        tds = tr.find_all("td")
        if not tds:
            continue
        parsed_day = parse_day_or_date_cell(tds[0].get_text(), row_idx)
        if not parsed_day:
            continue
        day_key, day_title, day_short, day_index, session_date = parsed_day
        day_occurrences[day_key] = day_occurrences.get(day_key, 0) + 1
        has_blue_font = bool(tds[0].find("font", attrs={"color": re.compile(r"#0000ff", re.I)}))
        week_key = '1' if session_date else ('2' if has_blue_font or day_occurrences[day_key] == 2 else '1')
        if day_key in weeks[week_key]:
            raise ValueError(f'Неоднозначные строки расписания: {week_key}/{day_key}')
        pairs_list = []
        for pair_idx, td in enumerate(tds[1 : 1 + max_pairs]):
            bell = bells[pair_idx] if pair_idx < len(bells) else {"number": pair_idx + 1, "label": f"{pair_idx + 1}-я", "start": "19:45", "end": "21:20"}
            cell_txt = td.get_text(" ")
            lessons = (
                parse_teacher_cell_lessons(cell_txt, teacher_name=owner_name, section=section)
                if is_teacher
                else parse_cell_lessons(cell_txt)
            )
            total_lessons += len(lessons)
            pairs_list.append({
                "number": bell["number"],
                "label": bell["label"],
                "start": bell["start"],
                "end": bell["end"],
                "is_empty": len(lessons) == 0,
                "lessons": lessons,
            })
        weeks[week_key][day_key] = {
            "day_key": day_key,
            "day_title": day_title,
            "day_short": day_short,
            "day_index": day_index,
            "session_date": session_date,
            "pairs": pairs_list,
        }
    return {"bells": bells, "weeks": weeks, "total_lessons": total_lessons}


def parse_group_schedule_html(html: str, group_id: str = "1", section: str = "bakalavriat") -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    group_name = group_id
    for f in soup.find_all("font", attrs={"color": re.compile(r"#ff00ff", re.I)}):
        if clean_text(f.get_text()):
            group_name = clean_text(f.get_text())
            break
    parsed = parse_14row_table(soup.find("table"), is_teacher=False, owner_name=group_name, section=section)
    source_file = f'{section}/{group_id}.htm'
    for days in parsed['weeks'].values():
        for day in days.values():
            for pair in day['pairs']:
                for lesson in pair['lessons']:
                    lesson.update(source_type='group_table', source_file=source_file)
    return {
        "mode": "student",
        "source_file": source_file,
        "source_type": "group_table",
        "group_id": group_id,
        "group_name": group_name,
        "norm_group_name": normalize_group_name(group_name),
        "section": section,
        "section_title": SECTIONS.get(section, section),
        "bells": parsed["bells"],
        "weeks": parsed["weeks"],
        "total_lessons": parsed["total_lessons"],
    }


def parse_departments_list_html(html: str, section: str = "bakalavriat") -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    institutes = []
    for div in soup.find_all("div", class_="faculty"):
        h2 = div.find(["h2", "h3"])
        inst_title = clean_text(h2.get_text()) if h2 else "Общеуниверситетские подразделения"
        depts = []
        for a in div.find_all("a"):
            href, name = (a.get("href") or "").strip(), clean_text(a.get_text())
            if href and name:
                depts.append({"caf_id": href.replace(".htm", ""), "href": href, "name": name, "institute": inst_title, "section": section})
        if depts:
            institutes.append({"institute": inst_title, "departments": depts})
    return institutes


def parse_department_teachers_html(html: str, caf_id: str = "Caf5", section: str = "bakalavriat", department_name: str = "") -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    teachers_list = []
    for idx, table in enumerate(soup.find_all("table")):
        prev_font = table.find_previous("font", attrs={"color": re.compile(r"#ff00ff", re.I)})
        raw_name = clean_text(prev_font.get_text()) if prev_font else ''
        previous_table = table.find_previous('table')
        if not raw_name or (previous_table is not None and prev_font.find_previous('table') is not previous_table):
            LOGGER.warning('Teacher heading missing: %s/%s table %s', section, caf_id, idx + 1)
            continue
        profile = build_teacher_profile(raw_name, caf_id=caf_id, department_name=department_name)
        parsed = parse_14row_table(table, is_teacher=True, owner_name=raw_name, section=section)
        source_file = f'{section}/{caf_id}.htm'
        profile['department'] = department_name or profile['department']
        for days in parsed['weeks'].values():
            for day in days.values():
                for pair in day['pairs']:
                    for lesson in pair['lessons']:
                        lesson.update(source_type='official_caf', source_file=source_file)
        teachers_list.append({
            "mode": "teacher",
            "source_file": source_file,
            "source_type": "official_caf",
            "teacher_key": profile["key"],
            "teacher_name": profile["short_name"],
            "profile": profile,
            "caf_id": caf_id,
            "section": section,
            "bells": parsed["bells"],
            "weeks": parsed["weeks"],
        })
    return teachers_list


def merge_teacher_schedules(primary: Dict[str, Any], secondary: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not secondary:
        return primary
    merged = json.loads(json.dumps(primary))
    merged["merged_sections"] = list({primary.get("section", "bakalavriat"), secondary.get("section", "spezialitet")})
    for week_key in ("1", "2"):
        sec_week = secondary.get("weeks", {}).get(week_key, {})
        prim_week = merged.setdefault("weeks", {}).setdefault(week_key, {})
        for day_key, sec_day in sec_week.items():
            if day_key not in prim_week:
                prim_week[day_key] = deepcopy(sec_day)
                continue
            prim_pairs = prim_week[day_key].get("pairs", [])
            sec_pairs = sec_day.get("pairs", [])
            for pair in sec_pairs:
                target = next((existing for existing in prim_pairs if
                               (existing['number'], existing['start'], existing['end']) ==
                               (pair['number'], pair['start'], pair['end'])), None)
                if target is None:
                    target = {**deepcopy(pair), 'lessons': []}
                    prim_pairs.append(target)
                existing_raws = {(lesson.get('raw'), lesson.get('source_file'), lesson.get('subject'), lesson.get('groups'), lesson.get('room')) for lesson in target['lessons']}
                for lesson in pair.get('lessons', []):
                    key = (lesson.get('raw'), lesson.get('source_file'), lesson.get('subject'), lesson.get('groups'), lesson.get('room'))
                    if key not in existing_raws:
                        target['lessons'].append(deepcopy(lesson))
                        existing_raws.add(key)
                target['is_empty'] = not target['lessons']
            prim_pairs.sort(key=lambda pair: (pair['start'], pair['number']))
    return merged
