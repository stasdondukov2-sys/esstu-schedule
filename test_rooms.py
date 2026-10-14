import unittest
from rooms import build_rooms_index

class RoomsTest(unittest.TestCase):
    def test_collisions_and_duplicates(self):
        schedule = {'group_name': 'A', 'weeks': {'1': {'monday': {'pairs': [
            {'number': 1, 'start': '09:00', 'end': '10:35', 'lessons': [
                {'room': ' 0410 ', 'subject': 'Physics'},
                {'room': '0410', 'subject': 'Math'},
                {'room': '', 'subject': 'Remote'}]}]}}}}
        result = build_rooms_index([schedule, schedule])
        self.assertEqual(result['count'], 1)
        self.assertEqual(len(result['rooms'][0]['slots']['1:monday:1']), 2)
        self.assertEqual(result['rooms'][0]['room'], '0410')

if __name__ == '__main__':
    unittest.main()
