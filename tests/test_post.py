
from datetime import datetime
import unittest

from eve_mongoengine import EveMongoengine

from tests import BaseTest, Eve, SimpleDoc, ComplexDoc, LimitedDoc, WrongDoc, SETTINGS

class TestHttpPost(BaseTest, unittest.TestCase):
    def test_post_simple(self):
        now = datetime.now()
        response = self.client.post('/simpledoc/',
                                    data='{"a": "jimmy", "b": 23}',
                                    content_type='application/json')
        #XXX: eve's fault: This should be 201 Created instead of 200 OK
        self.assertEqual(response.status_code, 200)
        post_data = response.get_json()
        self.assertEqual(post_data['status'], "OK")
        _id = post_data['_id']
        response = self.client.get('/simpledoc/%s' % _id)
        get_data = response.get_json()
        # updated field must match
        self.assertEqual(post_data['updated'], get_data['updated'])

    def test_post_invalid_schema_type(self):
        response = self.client.post('/simpledoc/',
                                    data='{"a":123}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertIn('status', json_data)
        self.assertEqual(json_data['status'], "ERR")
        self.assertListEqual(json_data['issues'], [u"value of field 'a' must be of string type"])

    def test_post_invalid_schema_limits(self):
        # break min_length
        response = self.client.post('/limiteddoc/',
                                    data='{"a": "hi", "b": "ho", "c": "x", "d": "string > 10 chars", "e": "<10 chars"}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200) # WTF
        json_data = response.get_json()
        self.assertListEqual(json_data['issues'], [u"min length for field 'e' is 10"])
        # break max_length
        response = self.client.post('/limiteddoc/',
                                    data='{"a": "hi", "b": "ho", "c": "x", "d": "string > 10 chars", "e": "some very long text"}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200) # WTF
        json_data = response.get_json()
        self.assertListEqual(json_data['issues'], [u"max length for field 'd' is 10"])


    def test_post_invalid_schema_required(self):
        response = self.client.post('/limiteddoc/',
                                    data='{"b": "ho", "c": "x"}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200) # WTF
        json_data = response.get_json()
        self.assertListEqual(json_data['issues'], [u"required field(s) are missing: 'a'"])


    def test_post_invalid_schema_unique(self):
        response = self.client.post('/limiteddoc/',
                                    data='{"a": "hi", "b": "ho"}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        response = self.client.post('/limiteddoc/',
                                    data='{"a": "hi", "b": "ho"}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200) # WTF
        json_data = response.get_json()
        self.assertListEqual(json_data['issues'], [u"value 'ho' for field 'b' not unique"])


    def test_post_invalid_schema_min_max(self):
        response = self.client.post('/limiteddoc/',
                                    data='{"a": "xoxo", "b": "xaxa", "f": 3}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertListEqual(json_data['issues'], [u"min value for field 'f' is 5"])

        response = self.client.post('/limiteddoc/',
                                    data='{"a": "xuxu", "b": "xixi", "f": 15}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertListEqual(json_data['issues'], [u"max value for field 'f' is 10"])


    def test_bulk_insert(self):
        response = self.client.post('/simpledoc/',
                                    data='[{"a": "jimmy", "b": 23}, {"a": "stefanie", "b": 47}]',
                                    content_type='application/json')
        for result in response.get_json():
            self.assertEqual(result['status'], "OK")


    def test_bulk_insert_error(self):
        response = self.client.post('/simpledoc/',
                                    data='[{"a": "jimmy", "b": 23}, {"a": 111, "b": 47}]',
                                    content_type='application/json')
        data = response.get_json()
        self.assertEqual(data[0]['status'], "OK")
        self.assertEqual(data[1]['status'], "ERR")

