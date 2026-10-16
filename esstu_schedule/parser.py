import json
import logging
import re
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from threading import RLock
from typing import Any

from bs4 import BeautifulSoup

from .data.diagnostics import record_error, record_cell

ESSTU_BASE_URL = "https://portal.esstu.ru"

SECTIONS = {
    "bakalavriat": "Бакалавриат, специалитет",
    "spezialitet": "Магистратура, колледж, ДОУ",
    "zo1": "Заочное 1",
    "zo2": "Заочное 2",
}

DAYS_MAP = {
    "вск": ("sunday", "Воскресенье", "Вс", 6),
    "вос": ("sunday", "Воскресенье", "Вс", 6),
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
    "янв": 1,
    "фев": 2,
    "мар": 3,
    "апр": 4,
    "май": 5,
    "мая": 5,
    "июн": 6,
    "июл": 7,
    "авг": 8,
    "сен": 9,
    "окт": 10,
    "ноя": 11,
    "дек": 12,
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

TEACHERS_META_PATH = Path(__file__).resolve().parents[1] / "teachers_meta.json"
LOGGER = logging.getLogger(__name__)
META_LOCK = RLock()
AVATAR_ROOT = Path(__file__).resolve().parents[1] / "static"


def local_teacher_photo(value: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) > 128
        or not re.fullmatch(
            r"avatars/[A-Za-z0-9_-]+\.(?:png|jpe?g|webp)", value, re.IGNORECASE
        )
    ):
        return ""
    path = (AVATAR_ROOT / value).resolve()
    return (
        value if path.is_relative_to(AVATAR_ROOT.resolve()) and path.is_file() else ""
    )


def repair_mojibake(text: str) -> str:
    def repair(match):
        word = match.group()
        if not re.search(r"[РС]", word):
            return word
        try:
            decoded = word.encode("cp1251").decode("utf-8")
        except (UnicodeError, ValueError):
            return word
        return (
            decoded
            if len(decoded) < len(word) and re.search("[А-Яа-яЁё]", decoded)
            else word
        )

    return re.sub(r"\S+", repair, text or "")


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", repair_mojibake(text)).strip()


def normalize_group_name(name: str) -> str:
    """Нормализует название группы для защиты от плавающих URL (Issue #4: 78.htm -> 80.htm)."""
    s = clean_text(name).lower().replace("ё", "е").rstrip(".")
    return re.sub(r"\s+", " ", s)


@lru_cache(maxsize=4)
def _read_teachers_meta(path: str, modified_ns: int, size: int):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_teachers_meta() -> dict[str, dict[str, Any]]:
    try:
        stat = TEACHERS_META_PATH.stat()
        return deepcopy(
            _read_teachers_meta(str(TEACHERS_META_PATH), stat.st_mtime_ns, stat.st_size)
        )
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        LOGGER.warning("Could not read teacher metadata", exc_info=True)
        return {}


def save_teacher_meta_entry(teacher_key: str, entry: dict[str, Any]) -> dict[str, Any]:
    if entry.get("photo") and not local_teacher_photo(entry["photo"]):
        raise ValueError(
            "Фото должно быть существующим локальным файлом avatars/*.png, *.jpg или *.webp"
        )
    with META_LOCK:
        meta = load_teachers_meta()
        norm_key = normalize_teacher_key(teacher_key)
        existing = meta.get(norm_key, {})
        existing.update(entry)
        meta[norm_key] = existing
        TEACHERS_META_PATH.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
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


def build_teacher_profile(
    raw_name: str, caf_id: str = "", department_name: str = ""
) -> dict[str, Any]:
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
        "photo": local_teacher_photo(meta.get("photo")),
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


def get_week_num(target_dt: datetime | None = None) -> dict[str, Any]:
    ulan_ude_tz = timezone(timedelta(hours=8))
    if target_dt is None:
        target_dt = datetime.now(ulan_ude_tz)
    elif target_dt.tzinfo is None:
        target_dt = target_dt.replace(tzinfo=ulan_ude_tz)
    else:
        target_dt = target_dt.astimezone(ulan_ude_tz)
    ref_date = get_reference_date(target_dt)
    diff_weeks = (target_dt - ref_date).total_seconds() / (60 * 60 * 24 * 7)
    is_odd = (
        (int(diff_weeks) % 2 == 0)
        if diff_weeks >= 0
        else (int(diff_weeks + 1 / 7) % 2 != 0)
    )
    return {
        "week_number": 1 if is_odd else 2,
        "week_title": "I неделя" if is_odd else "II неделя",
        "reference_date": ref_date.strftime("%Y-%m-%d"),
    }


def extract_tags(text: str) -> list[str]:
    tags = []
    low = text.lower()
    for lang in ("англ", "франц", "нем", "кит"):
        if lang in low:
            tags.append(lang)
    for subgroup in ("1", "2"):
        if re.search(
            r"(?<!\d)"
            + subgroup
            + r"\s*(?:[-–]\s*[яй]\s*)?(?:п\s*/?\s*гр?\.?|подгрупп[а-яё]*|подгр\.?)(?![а-яё\d])",
            low,
        ):
            tags.append(f"{subgroup} п/г")
    return tags


def parse_single_lesson_chunk(chunk: str) -> dict[str, Any]:
    raw = clean_text(chunk)
    lesson_type, type_code, rest = "Занятие", "other", raw
    type_match = re.match(
        r"^(лек\.|пр\.|лаб\.|сем\.|конс\.|экз\.|зач\.)\s*(.*)$",
        raw,
        flags=re.IGNORECASE,
    )
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
    room_match = re.search(r"\bа\.?\s*([0-9А-Яа-яA-Za-z\-/]+(?:\s+и/[пд])?)\s*$", rest)
    if room_match:
        room = room_match.group(1).strip()
        rest = rest[: room_match.start()].strip()

    teacher, teacher_key, teacher_profile = "", "", None
    teacher_match = re.search(
        r"([А-ЯЁ][А-ЯЁа-яё\-]+\s+[А-ЯЁ]\.\s*[А-ЯЁ]\.(?:[А-ЯЁа-яё\.]+)?)\s*[-–—]?\s*$",
        rest,
    )
    if teacher_match:
        raw_t = teacher_match.group(1).strip()
        teacher = format_teacher_display_name(raw_t)
        teacher_key = normalize_teacher_key(raw_t)
        teacher_profile = build_teacher_profile(raw_t)
        rest = rest[: teacher_match.start()].strip()

    tags = extract_tags(raw)
    ambiguous = len(re.findall(r"\bа\.\s*\d", raw, re.IGNORECASE)) > 1 or room.endswith(
        ("-", "/")
    )
    if ambiguous:
        # Keep the original cell for inspection instead of assigning one teacher/room to several lessons.
        rest, lesson_type, type_code = (
            "Несколько занятий — сверьте с источником",
            "Требуется сверка",
            "other",
        )
        room, teacher, teacher_key, teacher_profile = "", "", "", None
    missing_subject = bool(teacher_match) and not rest
    warning = ""
    if ambiguous:
        warning = "В ячейке несколько аудиторий или неполный номер. Проверьте исходное расписание."
    elif missing_subject:
        rest, lesson_type = "Предмет не указан", "Требуется сверка"
        warning = "В ячейке указано только ФИО преподавателя. Название предмета отсутствует — сверьте с источником."
    elif re.search(r"\bа\.\s*\d|[А-ЯЁ][А-ЯЁа-яё-]+\s+[А-ЯЁ]\.\s*[А-ЯЁ]\.", rest):
        rest, lesson_type, type_code = (
            "Не удалось разобрать занятие — сверьте с источником",
            "Требуется сверка",
            "other",
        )
        warning = "В названии остались ФИО или обозначение аудитории. Проверьте исходную ячейку."
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
        "parse_warning": warning,
        **({"needs_review": True} if warning else {}),
    }


def parse_cell_lessons(cell_text: str) -> list[dict[str, Any]]:
    text = clean_text(cell_text)
    if not text or text in ("_", "-", "—"):
        return []
    parts = re.split(
        r"(?=(?:^|\s)(?:лек\.|пр\.|лаб\.|сем\.|экз\.|зач\.|конс\.))",
        text,
        flags=re.IGNORECASE,
    )
    parts = [clean_text(p) for p in parts if clean_text(p) and clean_text(p) != "_"]
    expanded_parts: list[str] = []
    base_prefix = ""
    for p in parts:
        m_pref = re.match(
            r"^(лек\.|пр\.|лаб\.|сем\.)\s*([А-ЯЁа-яё\s]+?)(?=\(|[А-ЯЁ]{2,})",
            p,
            flags=re.IGNORECASE,
        )
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
            if base_prefix and not re.match(
                r"^(лек\.|пр\.|лаб\.|сем\.)", sc_clean, flags=re.IGNORECASE
            ):
                if sc_clean.startswith("("):
                    sc_clean = base_prefix + sc_clean
            expanded_parts.append(sc_clean)
    final_parts = expanded_parts if expanded_parts else [text]
    return [parse_single_lesson_chunk(p) for p in final_parts]


def parse_teacher_cell_lessons(
    cell_text: str, teacher_name: str = "", section: str = "bakalavriat"
) -> list[dict[str, Any]]:
    text = clean_text(cell_text)
    if not text or text in ("_", "-", "—"):
        return []
    lesson_type, type_code, subject, before_subject, groups_str, room = (
        "Занятие",
        "other",
        text,
        text,
        "",
        "",
    )
    type_match = re.search(
        r"\b(лек\.|пр\.|лаб\.|сем\.|экз\.|зач\.|конс\.)\s*(.+)$",
        text,
        flags=re.IGNORECASE,
    )
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
    room_match = re.search(
        r"\bа\.\s*((?:[0-9][0-9А-Яа-яA-Za-z\-/]*|дист\.*|д\.о\.[/]*)(?:\s+и/[пд])?)",
        before_subject,
        flags=re.IGNORECASE,
    )
    if room_match:
        room = room_match.group(1).strip()
        groups_str = clean_text(before_subject[: room_match.start()])
        if not type_match:
            subject = (
                clean_text(before_subject[room_match.end() :])
                or "Предмет не указан в источнике"
            )
    else:
        groups_str = before_subject
    tags = extract_tags(text)
    return [
        {
            "raw": text,
            "type": lesson_type,
            "type_code": type_code,
            "subject": subject,
            "teacher": format_teacher_display_name(teacher_name)
            if teacher_name
            else "",
            "teacher_key": normalize_teacher_key(teacher_name) if teacher_name else "",
            "room": room,
            "groups": groups_str,
            "section": section,
            "section_badge": "Магистратура/Колледж"
            if section == "spezialitet"
            else "Бакалавриат",
            "tag": ", ".join(tags),
            "tags": tags,
        }
    ]


def parse_day_or_date_cell(
    raw_cell_text: str, fallback_row_idx: int = 0
) -> tuple[str, str, str, int, str] | None:
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
        date_label = f"{day_num:02d}.{mon_num:02d}" + (f".{year:04d}" if year else "")
        # A date without a year does not identify a weekday. Keep it as a dated row.
        try:
            datetime(year or 2000, mon_num, day_num)
        except ValueError:
            return None
        return (
            f"date_{date_label}",
            date_label,
            date_label,
            DAYS_MAP.get(prefix3, ("", "", "", -1))[3],
            date_label,
        )

    m_num = re.search(r"(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?", cleaned)
    if m_num:
        year = int(m_num.group(3)) if m_num.group(3) else None
        date_label = f"{int(m_num.group(1)):02d}.{int(m_num.group(2)):02d}" + (
            f".{year:04d}" if year else ""
        )
        try:
            datetime(year or 2000, int(m_num.group(2)), int(m_num.group(1)))
        except ValueError:
            return None
        return (
            f"date_{date_label}",
            date_label,
            date_label,
            DAYS_MAP.get(prefix3, ("", "", "", -1))[3],
            date_label,
        )
    if prefix3 in DAYS_MAP:
        day_key, day_title, day_short, day_index = DAYS_MAP[prefix3]
        return day_key, day_title, day_short, day_index, ""
    return None


def parse_groups_list_html(
    html: str, section: str = "bakalavriat"
) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
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
                groups.append(
                    {
                        "id": href.replace(".htm", ""),
                        "href": href,
                        "name": name,
                        "norm_name": normalize_group_name(name),
                        "course": course,
                        "section": section,
                        "section_title": SECTIONS.get(section, section),
                    }
                )
    return groups


class ScheduleStructureError(ValueError):
    """Source table cannot be assigned to weeks without guessing."""


def parse_14row_table(table, is_teacher=False, owner_name="", section="bakalavriat"):
    rows = table.find_all("tr", recursive=False) if table else []
    if not rows and table:
        rows = table.select(":scope > tbody > tr")
    if len(rows) < 3:
        raise ScheduleStructureError("Нет заголовков пар, времени или строк занятий")

    def cells(row):
        return row.find_all(["td", "th"], recursive=False)

    headers, times = cells(rows[0]), cells(rows[1])
    if len(headers) != len(times) or len(headers) < 2:
        raise ScheduleStructureError("Не совпадают столбцы заголовков и времени")
    bells, columns = [], []
    data_rows = []
    explicit_week = None
    for row in rows[2:]:
        tds = cells(row)
        if not tds or not clean_text(row.get_text(" ")):
            continue
        text = clean_text(row.get_text(" ")).lower()
        heading = re.fullmatch(
            r"(i{1,2}|[12])\s*недел[яи]\s*(?:\((?:не)?ч[её]тная\))?", text
        )
        if heading and len(tds) == 1:
            explicit_week = "1" if heading[1] in ("i", "1") else "2"
            continue
        if len(tds) != len(headers):
            raise ScheduleStructureError("Число ячеек строки не совпадает с заголовком")
        day = parse_day_or_date_cell(tds[0].get_text())
        if not day:
            raise ScheduleStructureError(
                "Не распознан день или дата: " + clean_text(tds[0].get_text())
            )
        data_rows.append((tds, day, explicit_week))
    if not data_rows:
        raise ScheduleStructureError("Нет распознанных дней занятий")
    for column in range(1, len(headers)):
        title, time = (
            clean_text(headers[column].get_text()),
            clean_text(times[column].get_text()),
        )
        content = any(
            clean_text(row[0][column].get_text()) not in ("", "_", "-")
            for row in data_rows
        )
        if not time and not content:
            continue  # Portal exports blank padding, including an unused eighth pair.
        match = re.fullmatch(r"(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})", time)
        number = re.fullmatch(r"(\d+)(?:-?я)?", title)
        if not match or not number or int(number[1]) != len(bells) + 1:
            raise ScheduleStructureError(
                "Не распознан номер или интервал пары: " + title + " / " + time
            )
        start, end = (value.zfill(5) for value in match.groups())
        if (
            not all(
                re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value)
                for value in (start, end)
            )
            or start >= end
        ):
            raise ScheduleStructureError("Некорректное время пары")
        bells.append(
            {
                "number": int(number[1]),
                "label": f"{number[1]}-я",
                "start": start,
                "end": end,
            }
        )
        columns.append(column)
    if not bells:
        raise ScheduleStructureError("Нет интервалов звонков")
    dated_only = all(day[4] for _, day, _ in data_rows)
    explicit = all(week for _, _, week in data_rows)
    # Exported portal format: two complete ordered Mon-Sat blocks. Font colour
    # is presentation only. Unknown/truncated/mixed layouts fail explicitly.
    structural = (
        len(data_rows) == 12
        and [day[3] for _, day, _ in data_rows] == list(range(6)) * 2
    )
    if not explicit and not dated_only and not structural:
        raise ScheduleStructureError(
            "Ожидались два полных блока Пн–Сб или явные заголовки недель"
        )
    if not explicit and any(week for _, _, week in data_rows):
        if not structural or any(
            week and week != str(index // 6 + 1)
            for index, (_, _, week) in enumerate(data_rows)
        ):
            raise ScheduleStructureError(
                "Заголовки недель противоречат структуре таблицы"
            )
    weeks, total = {"1": {}, "2": {}}, 0
    for index, (tds, day, heading_week) in enumerate(data_rows):
        key, title, short, day_index, date = day
        week = (
            heading_week if explicit else ("1" if dated_only else str(index // 6 + 1))
        )
        if key in weeks[week]:
            raise ScheduleStructureError(f"Повтор дня/даты: {week}/{key}")
        pairs = []
        for bell, column in zip(bells, columns):
            text = tds[column].get_text(" ")
            lessons = (
                parse_teacher_cell_lessons(text, owner_name, section)
                if is_teacher
                else parse_cell_lessons(text)
            )
            empty = clean_text(text) in ("", "_", "-", "—")
            review = any(
                lesson.get("parse_warning")
                or lesson.get("subject") == "Предмет не указан в источнике"
                for lesson in lessons
            )
            record_cell(empty=empty, lost=not empty and not lessons, review=review)
            total += len(lessons)
            pairs.append({**bell, "is_empty": not lessons, "lessons": lessons})
        weeks[week][key] = {
            "day_key": key,
            "day_title": title,
            "day_short": short,
            "day_index": day_index,
            "session_date": date,
            "pairs": pairs,
        }
    return {
        "bells": bells,
        "weeks": weeks,
        "total_lessons": total,
        "is_incomplete": False,
        "parse_errors": [],
    }


def parse_table_with_status(table, source, **kwargs):
    try:
        return parse_14row_table(table, **kwargs)
    except ScheduleStructureError as error:
        record_error(source, str(error))
        return {
            "bells": [],
            "weeks": {"1": {}, "2": {}},
            "total_lessons": 0,
            "is_incomplete": True,
            "parse_errors": [str(error)],
        }


def parse_group_schedule_html(
    html: str, group_id: str = "1", section: str = "bakalavriat"
) -> dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    # The semantic heading identifies the owner; font colour is presentation.
    prefix = []
    for node in soup.descendants:
        if getattr(node, "name", None) == "table":
            break
        if isinstance(node, str):
            prefix.append(str(node))
    heading = re.search(
        r"Расписание\s+занятий\s+учебной\s+группы\s*:\s*(.+)$",
        clean_text(" ".join(prefix)),
        re.I,
    )
    group_name = clean_text(heading.group(1)) if heading else ""
    if not group_name:
        font = soup.find("font", attrs={"color": re.compile(r"#ff00ff", re.I)})
        group_name = clean_text(font.get_text()) if font else group_id
    parsed = parse_table_with_status(
        soup.find("table"),
        f"{section}/{group_id}.htm",
        is_teacher=False,
        owner_name=group_name,
        section=section,
    )
    source_file = f"{section}/{group_id}.htm"
    for days in parsed["weeks"].values():
        for day in days.values():
            for pair in day["pairs"]:
                for lesson in pair["lessons"]:
                    lesson.update(source_type="group_table", source_file=source_file)
    return {
        "mode": "student",
        "source_file": source_file,
        "source_type": "group_table",
        "group_id": group_id,
        "group_name": group_name,
        "norm_group_name": normalize_group_name(group_name),
        "section": section,
        "section_title": SECTIONS.get(section, section),
        "is_incomplete": parsed["is_incomplete"],
        "parse_errors": parsed["parse_errors"],
        "bells": parsed["bells"],
        "weeks": parsed["weeks"],
        "total_lessons": parsed["total_lessons"],
    }


def parse_departments_list_html(
    html: str, section: str = "bakalavriat"
) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    institutes = []
    for div in soup.find_all("div", class_="faculty"):
        h2 = div.find(["h2", "h3"])
        inst_title = (
            clean_text(h2.get_text()) if h2 else "Общеуниверситетские подразделения"
        )
        depts = []
        for a in div.find_all("a"):
            href, name = (a.get("href") or "").strip(), clean_text(a.get_text())
            if href and name:
                depts.append(
                    {
                        "caf_id": href.replace(".htm", ""),
                        "href": href,
                        "name": name,
                        "institute": inst_title,
                        "section": section,
                    }
                )
        if depts:
            institutes.append({"institute": inst_title, "departments": depts})
    return institutes


def parse_department_teachers_html(
    html: str,
    caf_id: str = "Caf5",
    section: str = "bakalavriat",
    department_name: str = "",
) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    teachers_list = []
    for idx, table in enumerate(soup.find_all("table")):
        prev_font = table.find_previous(
            "font", attrs={"color": re.compile(r"#ff00ff", re.IGNORECASE)}
        )
        raw_name = clean_text(prev_font.get_text()) if prev_font else ""
        previous_table = table.find_previous("table")
        if not raw_name or (
            previous_table is not None
            and prev_font.find_previous("table") is not previous_table
        ):
            record_error(
                f"{section}/{caf_id}.htm", f"Teacher heading missing: table {idx + 1}"
            )
            continue
        profile = build_teacher_profile(
            raw_name, caf_id=caf_id, department_name=department_name
        )
        parsed = parse_table_with_status(
            table,
            f"{section}/{caf_id}.htm#{raw_name}",
            is_teacher=True,
            owner_name=raw_name,
            section=section,
        )
        source_file = f"{section}/{caf_id}.htm"
        profile["department"] = department_name or profile["department"]
        for days in parsed["weeks"].values():
            for day in days.values():
                for pair in day["pairs"]:
                    for lesson in pair["lessons"]:
                        lesson.update(
                            source_type="official_caf", source_file=source_file
                        )
        teachers_list.append(
            {
                "mode": "teacher",
                "source_file": source_file,
                "source_type": "official_caf",
                "teacher_key": profile["key"],
                "teacher_name": profile["short_name"],
                "profile": profile,
                "caf_id": caf_id,
                "section": section,
                "is_incomplete": parsed["is_incomplete"],
                "parse_errors": parsed["parse_errors"],
                "bells": parsed["bells"],
                "weeks": parsed["weeks"],
            }
        )
    return teachers_list


def merge_teacher_schedules(
    primary: dict[str, Any], secondary: dict[str, Any] | None
) -> dict[str, Any]:
    if not secondary:
        return primary
    merged = json.loads(json.dumps(primary))
    merged["is_incomplete"] = bool(
        primary.get("is_incomplete") or secondary.get("is_incomplete")
    )
    merged["parse_errors"] = primary.get("parse_errors", []) + secondary.get(
        "parse_errors", []
    )
    merged["merged_sections"] = list(
        {primary.get("section", "bakalavriat"), secondary.get("section", "spezialitet")}
    )
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
                target = next(
                    (
                        existing
                        for existing in prim_pairs
                        if (existing["number"], existing["start"], existing["end"])
                        == (pair["number"], pair["start"], pair["end"])
                    ),
                    None,
                )
                if target is None:
                    target = {**deepcopy(pair), "lessons": []}
                    prim_pairs.append(target)
                existing_raws = {
                    (
                        lesson.get("raw"),
                        lesson.get("source_file"),
                        lesson.get("subject"),
                        lesson.get("groups"),
                        lesson.get("room"),
                    )
                    for lesson in target["lessons"]
                }
                for lesson in pair.get("lessons", []):
                    key = (
                        lesson.get("raw"),
                        lesson.get("source_file"),
                        lesson.get("subject"),
                        lesson.get("groups"),
                        lesson.get("room"),
                    )
                    if key not in existing_raws:
                        target["lessons"].append(deepcopy(lesson))
                        existing_raws.add(key)
                target["is_empty"] = not target["lessons"]
            prim_pairs.sort(key=lambda pair: (pair["start"], pair["number"]))
    return merged
