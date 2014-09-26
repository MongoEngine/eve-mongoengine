
import json
import time
import unittest
from eve.utils import config
from tests import BaseTest, SimpleDoc, ComplexDoc


def post_simple_item(f):
    def wrapper(self):
        response = self.client.post('/simpledoc/',
                                    data='{"a": "jimmy", "b": 23}',
                                    content_type='application/json')
        json_data = response.get_json()
        self._id = json_data[config.ID_FIELD]
        self.url = '/simpledoc/%s' % self._id # json_data[config.ID_FIELD]
        #response = self.client.get(self.url).get_json()
        self.etag = json_data[config.ETAG]
        self.updated = json_data[config.LAST_UPDATED]
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
        self._id = json_data[config.ID_FIELD]
        self.url = '/complexdoc/%s' % json_data[config.ID_FIELD]
        self.etag = json_data[config.ETAG]
        # check if etags are okay
        self.assertEqual(self.client.get(self.url).get_json()[config.ETAG], self.etag)
        #self._id = response[config.ID_FIELD]
        self.updated = json_data[config.LAST_UPDATED]
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

    def test_patch_subresource(self):
        # create new resource and subresource
        s = SimpleDoc(a="Answer to everything", b=42).save()
        d = ComplexDoc(l=['a', 'b'], n=999, r=s).save()

        response = self.client.get('/simpledoc/%s/complexdoc/%s' % (s.id, d.id))
        etag = response.get_json()[config.ETAG]
        headers = [('If-Match', etag)]

        # patch document
        patch_data = {'l': ['x', 'y', 'z'], 'r': str(s.id)}
        patch_url = '/simpledoc/%s/complexdoc/%s' % (s.id, d.id)
        response = self.client.patch(patch_url, data=json.dumps(patch_data),
                                     content_type='application/json', headers=headers)
        self.assertEqual(response.status_code, 200)
        resp_json = response.get_json()
        self.assertEqual(resp_json[config.STATUS], "OK")

        # check, if really edited
        response = self.client.get('/simpledoc/%s/complexdoc/%s' % (s.id, d.id))
        json_data = response.get_json()
        self.assertListEqual(json_data['l'], ['x', 'y', 'z'])
        self.assertEqual(json_data['n'], 999)

        # cleanup
        s.delete()
        d.delete()

    @post_simple_item
    def test_update_date_consistency(self):
        # tests if _updated is really updated when PATCHing resource
        updated = self.client.get(self.url).get_json()[config.LAST_UPDATED]
        time.sleep(1)
        s = SimpleDoc.objects.get()
        updated_before_patch = s.updated
        s.a = "bob"
        s.save()
        updated_after_patch = s.updated
        self.assertNotEqual(updated_before_patch, updated_after_patch)
        delta = updated_after_patch - updated_before_patch
        self.assertGreater(delta.seconds, 0)