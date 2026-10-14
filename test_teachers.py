import unittest
from teachers import teachers_from_groups

class TeacherIndexTest(unittest.TestCase):
    def test_preserves_source_and_deduplicates(self):
        schedule = {'section': 'bakalavriat', 'group_name': 'A', 'weeks': {'1': {'monday': {
            'pairs': [{'number': 2, 'start': '10:45', 'end': '12:20', 'lessons': [
                {'teacher': 'Семёнов А.В.', 'subject': 'Физика', 'room': '0410'},
                {'teacher': '', 'subject': 'Без преподавателя'}]}]}}}}
        teachers = teachers_from_groups([schedule, schedule])
        self.assertEqual(len(teachers), 1)
        teacher = teachers[0]
        self.assertTrue(teacher['partial'])
        pair = teacher['weeks']['1']['monday']['pairs'][0]
        self.assertEqual(len(pair['lessons']), 1)
        self.assertEqual(pair['lessons'][0]['groups'], 'A')
        self.assertEqual(pair['lessons'][0]['subject'], 'Физика')
        self.assertEqual(pair['start'], '10:45')

    def test_no_invented_teachers(self):
        self.assertEqual(teachers_from_groups([]), [])

if __name__ == '__main__':
    unittest.main()
