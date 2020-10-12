import json
import unittest
from eve.utils import config
from tests import BaseTest, SimpleDoc, ComplexDoc


class TestHttpPut(BaseTest, unittest.TestCase):
    def setUp(self):
        response = self.client.post(
            "/simpledoc/",
            data='{"a": "jimmy", "b": 23}',
            content_type="application/json",
        )
        json_data = response.get_json()
        self.url = "/simpledoc/%s" % json_data[config.ID_FIELD]
        response = self.client.get(self.url).get_json()
        self.etag = response[config.ETAG]
        self._id = response[config.ID_FIELD]
        self.updated = response[config.LAST_UPDATED]

    def tearDown(self):
        SimpleDoc.objects().delete()

    def do_put(self, url=None, data=None, headers=None):
        if url is None:
            url = self.url
        if headers is None:
            headers = [("If-Match", self.etag)]
        return self.client.put(
            url, data=data, content_type="application/json", headers=headers
        )

    def test_unknown_id(self):
        response = self.do_put("/simpledoc/unknown", data='{"a": "greg"}')
        self.assertEqual(response.status_code, 404)

    def test_bad_etag(self):
        response = self.do_put(data='{"a": "greg"}', headers=(("If-Match", "blabla"),))
        self.assertEqual(response.status_code, 412)

    def test_ifmatch_missing(self):
        response = self.do_put(data='{"a": "greg"}', headers=())
        self.assertEqual(response.status_code, 428)

    def test_put_overwrite_all(self):
        response = self.do_put(data='{"a": "greg", "b": 300}')

        response = self.client.get(self.url).get_json()
        self.assertIn("a", response)
        self.assertEqual(response["a"], "greg")
        self.assertIn("b", response)
        self.assertEqual(response["b"], 300)

    def test_put_overwrite_subset(self):
        self.do_put(data='{"a": "greg"}')
        response = self.client.get(self.url).get_json()
        self.assertIn("a", response)
        self.assertEqual(response["a"], "greg")
        self.assertNotIn("b", response)

    def test_put_subresource(self):
        # create new resource and subresource
        s = SimpleDoc(a="Answer to everything", b=42).save()
        d = ComplexDoc(l=["a", "b"], n=999, r=s).save()

        response = self.client.get("/simpledoc/%s/complexdoc/%s" % (s.id, d.id))
        etag = response.get_json()[config.ETAG]
        headers = [("If-Match", etag)]

        # new putted document
        put_data = {"l": ["x", "y", "z"], "r": str(s.id)}
        put_url = "/simpledoc/%s/complexdoc/%s" % (s.id, d.id)
        response = self.client.put(
            put_url,
            data=json.dumps(put_data),
            content_type="application/json",
            headers=headers,
        )
        self.assertEqual(response.status_code, 200)
        resp_json = response.get_json()
        self.assertEqual(resp_json[config.STATUS], "OK")

        # check, if really edited
        response = self.client.get("/simpledoc/%s/complexdoc/%s" % (s.id, d.id))
        json_data = response.get_json()
        self.assertListEqual(json_data["l"], ["x", "y", "z"])
        self.assertNotIn("n", json_data)

        s.delete()
        d.delete()
