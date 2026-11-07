import io
import json
import unittest
from server import parse_events

class SearchTests(unittest.TestCase):
    def test_earlier_messages_and_private_events(self):
        events = [
            {'type':'event_msg','payload':{'type':'user_message','message':'earlier searchable request'}},
            {'type':'response_item','payload':{'type':'message','role':'assistant','phase':'analysis','content':[{'text':'private reasoning'}]}},
            {'type':'response_item','payload':{'type':'function_call_output','output':'private tool output'}},
            {'type':'event_msg','payload':{'type':'user_message','message':'latest request'}},
        ]
        result=parse_events(io.StringIO('\n'.join(json.dumps(e) for e in events)))
        self.assertIn('earlier searchable',result['searchText'])
        self.assertNotIn('private',result['searchText'])
        self.assertEqual(result['request'],'latest request')

    def test_bounded_text(self):
        line=json.dumps({'type':'event_msg','payload':{'type':'user_message','message':'x'*6000}})
        result=parse_events(io.StringIO('\n'.join([line]*30)))
        self.assertLessEqual(len(result['searchText']),65536)
