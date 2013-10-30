
import unittest

from tests import BaseTest, SimpleDoc

class TestHttpPatch(BaseTest, unittest.TestCase):
    def setUp(self):
        response = self.client.post('/simpledoc/',
                                    data='{"a": "jimmy", "b": 23}',
                                    content_type='application/json')
        json_data = response.get_json()
        self.url = '/simpledoc/%s' % json_data['_id']
        response = self.client.get(self.url).get_json()
        self.etag = response['etag']
        self._id = response['_id']
        self.updated = response['updated']

    def tearDown(self):
        SimpleDoc.objects().delete()

    def do_patch(self, url=None, data=None, headers=None):
        if url is None:
            url = self.url
        if headers is None:
            headers=[('If-Match', self.etag)]
        return self.client.patch(url, data=data,
                                 content_type='application/json',
                                 headers=headers)

    def test_patch_overwrite_all(self):
        self.do_patch(data='{"a": "greg", "b": 300}')
        response = self.client.get(self.url).get_json()
        self.assertIn('a', response)
        self.assertEqual(response['a'], "greg")
        self.assertIn('b', response)
        self.assertEqual(response['b'], 300)

    def test_patch_overwrite_subset(self):
        self.do_patch(data='{"a": "greg"}')
        response = self.client.get(self.url).get_json()
        self.assertIn('a', response)
        self.assertEqual(response['a'], "greg")
        self.assertIn('b', response)
        self.assertEqual(response['b'], 23)