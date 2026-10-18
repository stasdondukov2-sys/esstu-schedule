"""Room tails observed in frozen portal HTML must not swallow the subject."""

import pytest

from parser import parse_single_lesson_chunk
from rooms import build_rooms_index
from teachers import teachers_from_groups


@pytest.mark.parametrize(
    "raw,subject,teacher,room,note",
    [
        (
            "лек.Технология и оборудование машиностроения ХАДЫКОВ М.Т. а.8233 смук",
            "Технология и оборудование машиностроения",
            "Хадыков М.Т.",
            "8233",
            "смук",
        ),
        (
            "пр.ЭД3 Big Data ГАРМАЕВ Э.Б. а.25-116 д/к",
            "ЭД3 Big Data",
            "Гармаев Э.Б.",
            "25-116",
            "д/к",
        ),
        (
            "лек.ЭД3 Big Data ТИМОФЕЕВ А.Н. а.25-115 л",
            "ЭД3 Big Data",
            "Тимофеев А.Н.",
            "25-115",
            "л",
        ),
        (
            "лаб.Физика древесины ЗОНХИЕВ М.М. а.1-13 д/к пгс",
            "Физика древесины",
            "Зонхиев М.М.",
            "1-13",
            "д/к пгс",
        ),
        (
            "пр.Основы строительных конструкций КАУРОВ А.И. а.1-12 л/пгс",
            "Основы строительных конструкций",
            "Кауров А.И.",
            "1-12",
            "л/пгс",
        ),
        (
            "пр.Основы строительных конструкций КАУРОВ А.И. а.1-12л пгс",
            "Основы строительных конструкций",
            "Кауров А.И.",
            "1-12л",
            "пгс",
        ),
        (
            "пр.Технологические процессы в строительстве ГОРБУНОВА Н.Ю. а.1-13д/к пгс",
            "Технологические процессы в строительстве",
            "Горбунова Н.Ю.",
            "1-13",
            "д/к пгс",
        ),
        (
            "лек.Безопасность жизнедеятельности ПЛИШКИНА О.В. а.8240 эбж",
            "Безопасность жизнедеятельности",
            "Плишкина О.В.",
            "8240",
            "эбж",
        ),
        (
            "лек.Основы безопасности и защиты Родины РИНЧИНОВА С.Б. а.8236 и/дэкол",
            "Основы безопасности и защиты Родины",
            "Ринчинова С.Б.",
            "8236 и/д",
            "экол",
        ),
        (
            "лек.Математика ПЕТРОВ И.И. а.8241 экол",
            "Математика",
            "Петров И.И.",
            "8241",
            "экол",
        ),
        (
            "лек.Математика ПЕТРОВ И.И. а.8234 геол",
            "Математика",
            "Петров И.И.",
            "8234",
            "геол",
        ),
        (
            "лек.Математика ПЕТРОВ И.И. а.8425 н/х",
            "Математика",
            "Петров И.И.",
            "8425",
            "н/х",
        ),
        (
            "лек.Математика ПЕТРОВ И.И. а.1-03 тэс",
            "Математика",
            "Петров И.И.",
            "1-03",
            "тэс",
        ),
        (
            "лек.Математика ПЕТРОВ И.И. а.1-44а д/кл",
            "Математика",
            "Петров И.И.",
            "1-44а",
            "д/кл",
        ),
        (
            "лек.Математика ПЕТРОВ И.И. а.8-фил.ТМКП 1",
            "Математика",
            "Петров И.И.",
            "8-фил.ТМКП 1",
            "",
        ),
    ],
)
def test_room_annotations_preserve_subject_teacher_and_room(
    raw, subject, teacher, room, note
):
    lesson = parse_single_lesson_chunk(raw)
    assert (lesson["subject"], lesson["teacher"], lesson["room"]) == (
        subject,
        teacher,
        room,
    )
    assert lesson.get("room_note", "") == note
    assert lesson["raw"] == raw
    assert not lesson["parse_warning"] and not lesson.get("needs_review")


@pytest.mark.parametrize(
    "suffix",
    [
        "дист.",
        "дистанц.",
        "дист./об",
        "дист./об.",
        "дист.об",
        "дист.об.",
        "дист...",
        "дист....",
        "дист.....",
        "дист,,,",
        "он-лайн курс",
    ],
)
def test_remote_room_markers_are_online_not_physical_rooms(suffix):
    raw = "пр.Механика грунтов, основания и фундаменты ДАМДИНЖАПОВ Б.Ц. а." + suffix
    lesson = parse_single_lesson_chunk(raw)
    assert lesson["subject"] == "Механика грунтов, основания и фундаменты"
    assert lesson["teacher"] == "Дамдинжапов Б.Ц."
    assert lesson["room"] == "online" and lesson["room_note"] == suffix
    assert lesson["raw"] == raw and not lesson["parse_warning"]
    assert build_rooms_index([schedule(lesson)])["rooms"] == []


def schedule(lesson):
    return {
        "group_name": "A",
        "weeks": {
            "1": {
                "monday": {
                    "pairs": [
                        {
                            "number": 1,
                            "start": "09:00",
                            "end": "10:35",
                            "lessons": [lesson],
                        }
                    ]
                }
            }
        },
    }


def test_department_note_does_not_hide_teacher_or_duplicate_room():
    lesson = parse_single_lesson_chunk(
        "пр.Физика древесины ДОРЖИЕВА Е.В. СМАДИД а.1-67"
    )
    assert lesson["subject"] == "Физика древесины"
    assert lesson["teacher"] == "Доржиева Е.В."
    assert lesson["teacher_note"] == "СМАДИД"
    assert lesson["room"] == "1-67" and not lesson["parse_warning"]
    assert build_rooms_index([schedule(lesson)])["rooms"][0]["room"] == "1-67"
    teacher = teachers_from_groups([schedule(lesson)])[0]
    assert (
        teacher["weeks"]["1"]["monday"]["pairs"][0]["lessons"][0]["subject"]
        == "Физика древесины"
    )


@pytest.mark.parametrize(
    "raw",
    [
        "Математика ПЕТРОВ И.И. а.701 и/к",
        "Математика ПЕТРОВ И.И. а.701 неизвестная пометка",
        "Математика ПЕТРОВ И.И. а.701 д/к другой предмет",
        "Математика ПЕТРОВ И.И. а.701 смук а.702",
        "Математика ПЕТРОВ И.И. а.25-",
        "САМБУЕВ Г.Ж. - а.25-212 д/к",
    ],
)
def test_unresolved_source_still_requires_review(raw):
    lesson = parse_single_lesson_chunk(raw)
    assert lesson["parse_warning"] and lesson["needs_review"]
    assert lesson["raw"] == raw


def test_teacher_only_known_room_does_not_invent_subject():
    lesson = parse_single_lesson_chunk("САМБУЕВ Г.Ж. - а.25-212 д/к")
    assert (lesson["subject"], lesson["teacher"], lesson["room"]) == (
        "Предмет не указан",
        "Самбуев Г.Ж.",
        "25-212",
    )
