
from datetime import datetime
import unittest
import json
from distutils.version import LooseVersion

from eve_mongoengine import EveMongoengine

from eve.utils import config

from tests import BaseTest, Eve, SimpleDoc, ComplexDoc, LimitedDoc, \
                  WrongDoc, HawkeyDoc, SETTINGS, in_app_context

# Starting with Eve 0.5 - Validation errors response codes are configurable.
try:
    POST_VALIDATION_ERROR_CODE = config.VALIDATION_ERROR_STATUS
except AttributeError:
    POST_VALIDATION_ERROR_CODE = 422


class TestHttpPost(BaseTest, unittest.TestCase):

    def test_post_simple(self):
        now = datetime.now()
        response = self.client.post('/simpledoc/',
                                    data='{"a": "jimmy", "b": 23}',
                                    content_type='application/json')
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
        self.assertEqual(response.status_code, POST_VALIDATION_ERROR_CODE)
        json_data = response.get_json()
        self.assertIn(config.STATUS, json_data)
        self.assertEqual(json_data[config.STATUS], "ERR")
        self.assertDictEqual(json_data[config.ISSUES], {'a': "must be of string type"})

    def test_post_invalid_schema_limits(self):
        # break min_length
        response = self.client.post('/limiteddoc/',
                                    data='{"a": "hi", "b": "ho", "c": "x", "d": "<10 chars", "e": "<10 chars", "g": "val1"}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, POST_VALIDATION_ERROR_CODE)
        json_data = response.get_json()
        self.assertDictEqual(json_data[config.ISSUES], {'e': "min length is 10"})
        # break max_length
        response = self.client.post('/limiteddoc/',
                                    data='{"a": "hi", "b": "ho", "c": "x", "d": "string > 10 chars", "e": "some very long text", "g": "val2"}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, POST_VALIDATION_ERROR_CODE)
        json_data = response.get_json()
        self.assertDictEqual(json_data[config.ISSUES], {'d': "max length is 10"})


    def test_post_invalid_schema_required(self):
        response = self.client.post('/limiteddoc/',
                                    data='{"b": "ho", "c": "x"}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, POST_VALIDATION_ERROR_CODE)
        json_data = response.get_json()
        self.assertDictEqual(json_data[config.ISSUES], {'a': "required field"})

    def test_post_invalid_schema_choice(self):
        response = self.client.post('/limiteddoc/',
                                    data='{"a": "hi", "b": "ho", "c": "a"}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, POST_VALIDATION_ERROR_CODE)
        json_data = response.get_json()
        self.assertDictEqual(json_data[config.ISSUES], {'c': 'unallowed value a'})
        response = self.client.post('/limiteddoc/',
                                    data='{"a": "hi", "b": "ho", "g": "val4"}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, POST_VALIDATION_ERROR_CODE)
        json_data = response.get_json()
        self.assertDictEqual(json_data[config.ISSUES], {'g': 'unallowed value val4'})
        response = self.client.post('/limiteddoc/',
                                    data='{"a": "hi", "b": "ho", "g": "test value 1"}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, POST_VALIDATION_ERROR_CODE)
        json_data = response.get_json()
        self.assertDictEqual(json_data[config.ISSUES], {'g': 'unallowed value test value 1'})

    @unittest.skip("Currently exception is raised while managing other exception")
    def test_post_invalid_schema_unique(self):
        response = self.client.post('/limiteddoc/',
                                    data='{"a": "hi", "b": "ho"}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, 201)
        response = self.client.post('/limiteddoc/',
                                    data='{"a": "hi", "b": "ho"}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, POST_VALIDATION_ERROR_CODE)
        json_data = response.get_json()
        self.assertDictEqual(json_data[config.ISSUES], {'b': "value 'ho' is not unique"})


    def test_post_invalid_schema_min_max(self):
        response = self.client.post('/limiteddoc/',
                                    data='{"a": "xoxo", "b": "xaxa", "f": 3}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, POST_VALIDATION_ERROR_CODE)
        json_data = response.get_json()
        self.assertDictEqual(json_data[config.ISSUES], {'f': "min value is 5"})

        response = self.client.post('/limiteddoc/',
                                    data='{"a": "xuxu", "b": "xixi", "f": 15}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, POST_VALIDATION_ERROR_CODE)
        json_data = response.get_json()
        self.assertDictEqual(json_data[config.ISSUES], {'f': "max value is 10"})


    def test_bulk_insert(self):
        response = self.client.post('/simpledoc/',
                                    data='[{"a": "jimmy", "b": 23}, {"a": "stefanie", "b": 47}]',
                                    content_type='application/json')

        for result in response.get_json()[config.ITEMS]:
            self.assertEqual(result[config.STATUS], "OK")


    def test_bulk_insert_error(self):
        response = self.client.post('/simpledoc/',
                                    data='[{"a": "jimmy", "b": 23}, {"a": 111, "b": 47}]',
                                    content_type='application/json')
        data = response.get_json()[config.ITEMS]
        self.assertEqual(data[0][config.STATUS], "OK")
        self.assertEqual(data[1][config.STATUS], "ERR")

    @in_app_context
    def test_post_subresource(self):
        s = SimpleDoc(a="Answer to everything", b=42).save()
        data = {'l': ['x', 'y', 'z'], 'r': str(s.id)}
        post_url = '/simpledoc/%s/complexdoc' % s.id
        response = self.client.post(post_url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        resp_json = response.get_json()
        self.assertEqual(resp_json[config.STATUS], "OK")

        # verify saved data
        response = self.client.get('/simpledoc/%s/complexdoc' % s.id)
        self.assertEqual(response.status_code, 200)
        resp_json = response.get_json()
        self.assertEqual(len(resp_json[config.ITEMS]), 1)
        self.assertEqual(resp_json[config.ITEMS][0]['l'], ['x', 'y', 'z'])

    def test_post_with_pre_save_hook(self):
        # resulting etag has to match (etag must be computed from
        # modified data, not from original!)
        data = {'a': 'hey'}
        response = self.client.post('/hawkeydoc/', data=json.dumps(data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 201)
        resp_json = response.get_json()
        print(resp_json)
        self.assertEqual(resp_json[config.STATUS], "OK")
        etag = resp_json[config.ETAG]        
        # verify etag
        resp = self.client.get('/hawkeydoc/%s' % resp_json['_id'])
        print(resp.get_json())
        self.assertEqual(etag, resp.get_json()[config.ETAG])
