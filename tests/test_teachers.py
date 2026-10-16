import unittest
from copy import deepcopy

from parser import parse_teacher_cell_lessons
from teachers import combine_teacher_catalog, teachers_from_groups


class TeacherIndexTest(unittest.TestCase):
    def test_preserves_source_and_deduplicates(self):
        schedule = {
            "section": "bakalavriat",
            "group_name": "A",
            "weeks": {
                "1": {
                    "monday": {
                        "pairs": [
                            {
                                "number": 2,
                                "start": "10:45",
                                "end": "12:20",
                                "lessons": [
                                    {
                                        "teacher": "Семёнов А.В.",
                                        "subject": "Физика",
                                        "room": "0410",
                                    },
                                    {"teacher": "", "subject": "Без преподавателя"},
                                ],
                            }
                        ]
                    }
                }
            },
        }
        teachers = teachers_from_groups([schedule, schedule])
        self.assertEqual(len(teachers), 1)
        teacher = teachers[0]
        self.assertTrue(teacher["partial"])
        pair = teacher["weeks"]["1"]["monday"]["pairs"][0]
        self.assertEqual(len(pair["lessons"]), 1)
        self.assertEqual(pair["lessons"][0]["groups"], "A")
        self.assertEqual(pair["lessons"][0]["subject"], "Физика")
        self.assertEqual(pair["start"], "10:45")

    def test_no_invented_teachers(self):
        self.assertEqual(teachers_from_groups([]), [])

    def test_official_cell_without_type(self):
        lesson = parse_teacher_cell_lessons("1146 тпуп а.0410 и/д")[0]
        self.assertEqual(lesson["subject"], "Предмет не указан в источнике")
        self.assertEqual(lesson["groups"], "1146 тпуп")
        self.assertEqual(lesson["room"], "0410 и/д")
        lesson = parse_teacher_cell_lessons("К96/1 а.0425 География")[0]
        self.assertEqual(lesson["subject"], "География")

    def test_official_priority_and_group_supplement(self):
        lesson = {
            "subject": "Физика",
            "room": "0410",
            "groups": "A",
            "source_type": "official_caf",
            "source_file": "bakalavriat/Caf5.htm",
        }
        official = {
            "teacher_key": "A",
            "caf_id": "Caf5",
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
        derived = deepcopy(official)
        derived["caf_id"] = ""
        derived["weeks"]["1"]["monday"]["pairs"][0]["lessons"][0]["source_type"] = (
            "group_derived"
        )
        derived["weeks"]["1"]["monday"]["pairs"][0]["lessons"].append(
            {"subject": "Математика", "room": "0420"}
        )
        result = combine_teacher_catalog([official], [derived])[0]
        lessons = result["weeks"]["1"]["monday"]["pairs"][0]["lessons"]
        self.assertEqual(len(lessons), 2)
        self.assertEqual(lessons[0]["source_type"], "official_caf")
        self.assertEqual(result["caf_ids"], ["Caf5"])
        self.assertFalse(result["identity_ambiguous"])
        other_caf = deepcopy(official)
        other_caf["caf_id"] = "Caf6"
        candidate = combine_teacher_catalog([official, other_caf], [derived])[0]
        self.assertTrue(candidate["identity_ambiguous"])
        self.assertEqual(candidate["identity_source_caf_ids"], ["Caf5", "Caf6"])

        # The same subject and room do not imply the same group or lesson type.
        parallel = deepcopy(official)
        parallel_lesson = parallel["weeks"]["1"]["monday"]["pairs"][0]["lessons"][0]
        parallel_lesson["groups"] = "B"
        result = combine_teacher_catalog([official, parallel], [])[0]
        lessons = result["weeks"]["1"]["monday"]["pairs"][0]["lessons"]
        self.assertEqual([item["groups"] for item in lessons], ["A", "B"])
        parallel_lesson["groups"] = "A"
        parallel_lesson["type_code"] = "lab"
        result = combine_teacher_catalog([official, parallel], [])[0]
        self.assertEqual(len(result["weeks"]["1"]["monday"]["pairs"][0]["lessons"]), 2)


if __name__ == "__main__":
    unittest.main()
