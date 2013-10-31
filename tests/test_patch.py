
import unittest
from tests import BaseTest, SimpleDoc, ComplexDoc


def post_simple_item(f):
    def wrapper(self):
        response = self.client.post('/simpledoc/',
                                    data='{"a": "jimmy", "b": 23}',
                                    content_type='application/json')
        json_data = response.get_json()
        self.url = '/simpledoc/%s' % json_data['_id']
        response = self.client.get(self.url).get_json()
        self.etag = response['etag']
        self._id = response['_id']
        self.updated = response['updated']
        f(self)
        SimpleDoc.objects().delete()
    return wrapper

def post_complex_item(f):
    def wrapper(self):
        payload = '{"i": {"a": "hello"}, "d": {"x": null}, "l": ["m", "n"]}'
        response = self.client.post('/complexdoc/',
                                    data=payload,
                                    content_type='application/json')
        json_data = response.get_json()
        self.url = '/complexdoc/%s' % json_data['_id']
        response = self.client.get(self.url).get_json()
        self.etag = response['etag']
        self._id = response['_id']
        self.updated = response['updated']
        f(self)
        ComplexDoc.objects().delete()
    return wrapper


class TestHttpPatch(BaseTest, unittest.TestCase):

    def do_patch(self, url=None, data=None, headers=None):
        if url is None:
            url = self.url
        if headers is None:
            headers=[('If-Match', self.etag)]
        return self.client.patch(url, data=data,
                                 content_type='application/json',
                                 headers=headers)

    @post_simple_item
    def test_patch_overwrite_all(self):
        self.do_patch(data='{"a": "greg", "b": 300}')
        response = self.client.get(self.url).get_json()
        self.assertIn('a', response)
        self.assertEqual(response['a'], "greg")
        self.assertIn('b', response)
        self.assertEqual(response['b'], 300)

    @post_simple_item
    def test_patch_overwrite_subset(self):
        self.do_patch(data='{"a": "greg"}')
        response = self.client.get(self.url).get_json()
        self.assertIn('a', response)
        self.assertEqual(response['a'], "greg")
        self.assertIn('b', response)
        self.assertEqual(response['b'], 23)

    @post_complex_item
    def test_patch_dict_field(self):
        self.assertEqual(ComplexDoc.objects[0].d['x'], None)
        response = self.do_patch(data='{"d": {"x": "789"}}')
        self.assertEqual(ComplexDoc.objects[0].d['x'], "789")

    @post_complex_item
    def test_patch_embedded_document(self):
        self.assertEqual(ComplexDoc.objects[0].i.a, "hello")
        response = self.do_patch(data='{"i": {"a": "bye"}}')
        self.assertEqual(ComplexDoc.objects[0].i.a, "bye")

    @post_complex_item
    def test_patch_list(self):
        self.assertEqual(ComplexDoc.objects[0].l, ["m", "n"])
        response = self.do_patch(data='{"l": []}')
        self.assertEqual(ComplexDoc.objects[0].l, [])
        
