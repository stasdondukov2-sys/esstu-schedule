import unittest
from parser import parse_single_lesson_chunk, parse_teacher_cell_lessons, extract_tags


class StudyParsingTests(unittest.TestCase):
    def test_subgroup_markers(self):
        self.assertEqual(extract_tags('11 п/г'), [])
        self.assertEqual(extract_tags('Физика 1'), [])
        self.assertEqual(extract_tags('1-я подгруппа'), ['1 п/г'])
        self.assertEqual(extract_tags('2 п/г'), ['2 п/г'])

    def test_attestation_types_for_groups_and_teachers(self):
        for prefix, expected in [('экз.', 'exam'), ('зач.', 'test'), ('конс.', 'consultation')]:
            with self.subTest(prefix=prefix):
                self.assertEqual(parse_single_lesson_chunk(prefix + ' Физика')['type_code'], expected)
                self.assertEqual(parse_teacher_cell_lessons('1146 а.0410 ' + prefix + ' Физика')[0]['type_code'], expected)


if __name__ == '__main__':
    unittest.main()
