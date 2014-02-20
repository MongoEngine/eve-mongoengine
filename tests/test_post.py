
from datetime import datetime
import unittest
import json

from eve_mongoengine import EveMongoengine
from eve.utils import config
from tests import BaseTest, Eve, SimpleDoc, ComplexDoc, LimitedDoc, WrongDoc, SETTINGS

class TestHttpPost(BaseTest, unittest.TestCase):
    def test_post_simple(self):
        now = datetime.now()
        response = self.client.post('/simpledoc/',
                                    data='{"a": "jimmy", "b": 23}',
                                    content_type='application/json')
        #XXX: eve's fault: This should be 201 Created instead of 200 OK
        self.assertEqual(response.status_code, 201)
        post_data = response.get_json()
        self.assertEqual(post_data[config.STATUS], "OK")
        _id = post_data['_id']
        response = self.client.get('/simpledoc/%s' % _id)
        get_data = response.get_json()
        # updated field must match
        self.assertEqual(post_data[config.LAST_UPDATED], get_data[config.LAST_UPDATED])

    def test_post_invalid_schema_type(self):
        response = self.client.post('/simpledoc/',
                                    data='{"a":123}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertIn(config.STATUS, json_data)
        self.assertEqual(json_data[config.STATUS], "ERR")
        self.assertDictEqual(json_data[config.ISSUES], {'a': "must be of string type"})

    def test_post_invalid_schema_limits(self):
        # break min_length
        response = self.client.post('/limiteddoc/',
                                    data='{"a": "hi", "b": "ho", "c": "x", "d": "<10 chars", "e": "<10 chars"}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200) # WTF
        json_data = response.get_json()
        self.assertDictEqual(json_data[config.ISSUES], {'e': "min length is 10"})
        # break max_length
        response = self.client.post('/limiteddoc/',
                                    data='{"a": "hi", "b": "ho", "c": "x", "d": "string > 10 chars", "e": "some very long text"}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200) # WTF
        json_data = response.get_json()
        self.assertDictEqual(json_data[config.ISSUES], {'d': "max length is 10"})


    def test_post_invalid_schema_required(self):
        response = self.client.post('/limiteddoc/',
                                    data='{"b": "ho", "c": "x"}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200) # WTF
        json_data = response.get_json()
        self.assertDictEqual(json_data[config.ISSUES], {'a': "required field"})


    def test_post_invalid_schema_unique(self):
        response = self.client.post('/limiteddoc/',
                                    data='{"a": "hi", "b": "ho"}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, 201)
        response = self.client.post('/limiteddoc/',
                                    data='{"a": "hi", "b": "ho"}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200) # WTF
        json_data = response.get_json()
        self.assertDictEqual(json_data[config.ISSUES], {'b': "value 'ho' is not unique"})


    def test_post_invalid_schema_min_max(self):
        response = self.client.post('/limiteddoc/',
                                    data='{"a": "xoxo", "b": "xaxa", "f": 3}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertDictEqual(json_data[config.ISSUES], {'f': "min value is 5"})

        response = self.client.post('/limiteddoc/',
                                    data='{"a": "xuxu", "b": "xixi", "f": 15}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertDictEqual(json_data[config.ISSUES], {'f': "max value is 10"})


    def test_bulk_insert(self):
        response = self.client.post('/simpledoc/',
                                    data='[{"a": "jimmy", "b": 23}, {"a": "stefanie", "b": 47}]',
                                    content_type='application/json')
        for result in response.get_json():
            self.assertEqual(result[config.STATUS], "OK")


    def test_bulk_insert_error(self):
        response = self.client.post('/simpledoc/',
                                    data='[{"a": "jimmy", "b": 23}, {"a": 111, "b": 47}]',
                                    content_type='application/json')
        data = response.get_json()
        self.assertEqual(data[0][config.STATUS], "OK")
        self.assertEqual(data[1][config.STATUS], "ERR")

    def test_post_subresource(self):
        s = SimpleDoc(a="Answer to everything", b=42).save()
        data = {'l': ['x', 'y', 'z'], 'r': str(s.id)}
        post_url = '/simpledoc/%s/complexdoc' % s.id
        response = self.client.post(post_url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        resp_json = response.get_json()
        self.assertEqual(resp_json[config.STATUS], "OK")

        # overeni, jestli tam opravdu je.
        response = self.client.get('/simpledoc/%s/complexdoc' % s.id)
        self.assertEqual(response.status_code, 200)
        resp_json = response.get_json()
        self.assertEqual(len(resp_json[config.ITEMS]), 1)
        self.assertEqual(resp_json[config.ITEMS][0]['l'], ['x', 'y', 'z'])
