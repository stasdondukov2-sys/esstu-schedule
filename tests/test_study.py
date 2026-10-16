import json
import unittest
from pathlib import Path

import pytest

from parser import extract_tags, parse_single_lesson_chunk, parse_teacher_cell_lessons


def test_teacher_only_chunks_keep_identity_without_inventing_subject():
    rows = json.loads(
        (Path(__file__).parent / "fixtures/teacher-only-chunks.json").read_text(
            encoding="utf-8"
        )
    )
    for row in rows:
        lesson = parse_single_lesson_chunk(row["raw"])
        assert lesson["subject"] == "Предмет не указан"
        assert lesson["type"] == "Требуется сверка"
        assert lesson["teacher"] == row["teacher"]
        assert lesson["room"] == row["room"]
        assert lesson["parse_warning"]
        assert lesson["raw"] == row["raw"]


def test_teacher_suffix_does_not_hide_a_real_subject():
    lesson = parse_single_lesson_chunk("лек. Математика ДАНЗАНОВА С.В. - а.0105")
    assert lesson["subject"] == "Математика"
    assert lesson["teacher"] == "Данзанова С.В."
    assert not lesson["parse_warning"]


@pytest.mark.parametrize(
    "raw,subject,teacher",
    [
        (
            "Экономическая теория АЛЕКСЕЕВА Г.Е. а.701 и/п",
            "Экономическая теория",
            "Алексеева Г.Е.",
        ),
        (
            "Правовые основы профессиональной деятельности УХИНЖАПОВА Э.В. а.701 и/п",
            "Правовые основы профессиональной деятельности",
            "Ухинжапова Э.В.",
        ),
    ],
)
def test_teacher_and_room_with_panel_annotation(raw, subject, teacher):
    from rooms import build_rooms_index
    from teachers import teachers_from_groups

    lesson = parse_single_lesson_chunk(raw)
    assert (lesson["subject"], lesson["teacher"], lesson["room"]) == (
        subject,
        teacher,
        "701 и/п",
    )
    assert not lesson["parse_warning"] and not lesson.get("needs_review")
    schedule = {
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
    assert (
        teachers_from_groups([schedule])[0]["weeks"]["1"]["monday"]["pairs"][0][
            "lessons"
        ][0]["subject"]
        == subject
    )
    assert build_rooms_index([schedule])["rooms"][0]["room"] == "701"


def test_unrecognized_room_annotation_requests_review():
    raw = "Экономика АЛЕКСЕЕВА Г.Е. а.701 и/к"
    lesson = parse_single_lesson_chunk(raw)
    assert lesson["needs_review"] and lesson["parse_warning"]
    assert lesson["raw"] == raw
    assert lesson["room"] == ""


class StudyParsingTests(unittest.TestCase):
    def test_subgroup_markers(self):
        self.assertEqual(extract_tags("11 п/г"), [])
        self.assertEqual(extract_tags("Физика 1"), [])
        self.assertEqual(extract_tags("1-я подгруппа"), ["1 п/г"])
        self.assertEqual(extract_tags("2 п/г"), ["2 п/г"])

    def test_attestation_types_for_groups_and_teachers(self):
        for prefix, expected in [
            ("экз.", "exam"),
            ("зач.", "test"),
            ("конс.", "consultation"),
        ]:
            with self.subTest(prefix=prefix):
                self.assertEqual(
                    parse_single_lesson_chunk(prefix + " Физика")["type_code"], expected
                )
                self.assertEqual(
                    parse_teacher_cell_lessons("1146 а.0410 " + prefix + " Физика")[0][
                        "type_code"
                    ],
                    expected,
                )


if __name__ == "__main__":
    unittest.main()
