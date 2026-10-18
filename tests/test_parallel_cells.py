from pathlib import Path

import pytest

from parser import parse_cell_lessons, parse_group_schedule_html
from rooms import build_rooms_index
from teachers import teachers_from_groups


@pytest.mark.parametrize(
    "subject", ["Операционные системы", "Мобильная операционная система"]
)
def test_shared_subject_is_repeated_for_both_teachers_without_inventing_subgroups(
    subject,
):
    raw = f"лаб.{subject} ГЛУШКОВА И.И. а.25-214 д/к ГАРМАЕВ Ч.Б. - а.25-312 д/к"
    lessons = parse_cell_lessons(raw)
    assert [
        (lesson["subject"], lesson["teacher"], lesson["room"]) for lesson in lessons
    ] == [
        (subject, "Глушкова И.И.", "25-214"),
        (subject, "Гармаев Ч.Б.", "25-312"),
    ]
    assert all(
        lesson["type_code"] == "lab" and not lesson["parse_warning"]
        for lesson in lessons
    )
    assert all(
        lesson["source_cell_raw"] == raw and not lesson["tags"] for lesson in lessons
    )
    assert lessons[1]["raw"] == "ГАРМАЕВ Ч.Б. - а.25-312 д/к"
    assert lessons[1]["subject_inherited"] and lessons[1]["type_inherited"]


def test_distinct_parallel_subjects_keep_their_own_explicit_subgroups():
    raw = "лаб.Веб-программирование для систем искусственного интеллекта 1- 1 п/г МЕРДЫГЕЕВ Б.Д. а.25-314 д/к Глубокое обучение- 2 п/г БАЖЕНОВ Н.А. - а.25-312 д/к"
    first, second = parse_cell_lessons(raw)
    assert (
        first["subject"]
        == "Веб-программирование для систем искусственного интеллекта 1- 1 п/г"
    )
    assert second["subject"] == "Глубокое обучение- 2 п/г"
    assert first["tags"] == ["1 п/г"] and second["tags"] == ["2 п/г"]
    assert first["teacher"] == "Мердыгеев Б.Д." and second["teacher"] == "Баженов Н.А."
    assert first["room"] == "25-314" and second["room"] == "25-312"
    assert not first["parse_warning"] and not second["parse_warning"]
    assert not second.get("subject_inherited")


@pytest.mark.parametrize(
    "raw",
    [
        "лаб.Физика ПЕТРОВ И.И. ИВАНОВ П.П. - а.0105- а.0107",
        "лаб.Физика ПЕТРОВ И.И. а.0105 ИВАНОВ П.П. СИДОРОВ С.С. - а.0107- а.0109",
        "лаб.Физика ПЕТРОВ И.И. а.0105 ИВАНОВ П.П. - а.25-",
        "лаб.Физика ПЕТРОВ И.И. а.0105 неизвестная пометка ИВАНОВ П.П. - а.0107",
        "лаб.Физика 1 п/г ПЕТРОВ И.И. а.0105 ИВАНОВ П.П. - а.0107",
        "ПЕТРОВ И.И. а.0105 ИВАНОВ П.П. - а.0107",
        "лаб.Физика ПЕТРОВ И. а.0105 ИВАНОВ П.П. - а.0107",
    ],
)
def test_independent_lists_incomplete_rooms_and_missing_subjects_are_not_guessed(raw):
    lessons = parse_cell_lessons(raw)
    assert any(lesson["parse_warning"] for lesson in lessons)
    assert not any(lesson.get("subject_inherited") for lesson in lessons)


def test_real_564_2_source_restores_all_eight_cells_and_correct_indexes():
    source = Path(__file__).resolve().parents[1] / "demo_data/bakalavriat/147.htm"
    schedule = parse_group_schedule_html(
        source.read_bytes().decode("cp1251"), "147", "bakalavriat"
    )
    assert schedule["group_name"] == "564-2"
    restored = [
        lesson
        for days in schedule["weeks"].values()
        for day in days.values()
        for pair in day["pairs"]
        for lesson in pair["lessons"]
        if lesson.get("source_cell_raw")
    ]
    assert len(restored) == 16
    assert not any(lesson["parse_warning"] for lesson in restored)
    pair = next(
        p for p in schedule["weeks"]["1"]["monday"]["pairs"] if p["number"] == 3
    )
    assert [lesson["subject"] for lesson in pair["lessons"]] == [
        "Операционные системы"
    ] * 2
    rooms = {r["room"]: r for r in build_rooms_index([schedule])["rooms"]}
    assert rooms["25-214"]["slots"]["1:monday:3"][0]["teacher"] == "Глушкова И.И."
    assert rooms["25-312"]["slots"]["1:monday:3"][0]["teacher"] == "Гармаев Ч.Б."
    teachers = teachers_from_groups([schedule])
    garmaev = next(t for t in teachers if t["profile"]["short_name"] == "Гармаев Ч.Б.")
    assert any(
        lesson["subject"] == "Операционные системы" and lesson["room"] == "25-312"
        for p in garmaev["weeks"]["1"]["monday"]["pairs"]
        for lesson in p["lessons"]
    )
