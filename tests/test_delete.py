
import unittest

from tests import BaseTest, SimpleDoc

class TestHttpDelete(BaseTest, unittest.TestCase):
    def setUp(self):
        response = self.client.post('/simpledoc/',
            data='[{"a": "jimmy", "b": 23}, {"a": "steve", "b": 77}]',
            content_type='application/json')
        json_data = response.get_json()
        ids = tuple(x['_id'] for x in json_data)
        url = '/simpledoc?where={"$or": [{"_id": "%s"}, {"_id": "%s"}]}' % ids
        response = self.client.get(url).get_json()
        item = response['_items'][0]
        self.etag = item['etag']
        self._id = item['_id']
        self._id2 = response['_items'][1]['_id']

    def tearDown(self):
        SimpleDoc.objects().delete()

    def delete(self, url):
        return self.client.delete(url, headers=[('If-Match', self.etag)])

    def test_delete_item(self):
        url = '/simpledoc/%s' % self._id
        r = self.delete(url)
        response = self.client.get('/simpledoc')
        self.assertEqual(response.status_code, 200)
        items = response.get_json()['_items']
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['_id'], self._id2)

    def test_delete_resource(self):
        r = self.delete('/simpledoc')
        response = self.client.get('/simpledoc')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()['_items']), 0)

    def test_delete_empty_resource(self):
        SimpleDoc.objects().delete()
        response = self.delete('/simpledoc')
        self.assertEqual(response.status_code, 200)

    def test_delete_unknown_item(self):
        url = '/simpledoc/%s' % 'abc'
        response = self.delete(url)
        self.assertEqual(response.status_code, 404)

    def test_delete_unknown_resource(self):
        response = self.delete('/unknown')
        self.assertEqual(response.status_code, 404)
        
