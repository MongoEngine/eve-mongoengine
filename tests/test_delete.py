import unittest

from eve.utils import config

from eve_mongoengine import get_utc_time
from tests import BaseTest, SimpleDoc, ComplexDoc, HawkeyDoc


class TestHttpDelete(BaseTest, unittest.TestCase):
    def setUp(self):
        response = self.client.post(
            "/simpledoc/",
            data='[{"a": "jimmy", "b": 23}, {"a": "steve", "b": 77}]',
            content_type="application/json",
        )
        json_data = response.get_json()
        ids = tuple(x["_id"] for x in json_data[config.ITEMS])
        url = '/simpledoc?where={"$or": [{"_id": "%s"}, {"_id": "%s"}]}' % ids
        response = self.client.get(url).get_json()
        item = response[config.ITEMS][0]
        self.etag = item[config.ETAG]
        self._id = item[config.ID_FIELD]
        self._id2 = response[config.ITEMS][1][config.ID_FIELD]

    def tearDown(self):
        SimpleDoc.objects().delete()

    def delete(self, url):
        return self.client.delete(url, headers=[("If-Match", self.etag)])

    def test_delete_item(self):
        url = "/simpledoc/%s" % self._id
        r = self.delete(url)
        self.assertEqual(r.status_code, 204)
        response = self.client.get("/simpledoc")
        self.assertEqual(response.status_code, 200)
        items = response.get_json()[config.ITEMS]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["_id"], self._id2)

    def test_delete_resource(self):
        r = self.delete("/simpledoc")
        response = self.client.get("/simpledoc")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()["_items"]), 0)

    def test_delete_empty_resource(self):
        SimpleDoc.objects().delete()
        response = self.delete("/simpledoc")
        self.assertEqual(response.status_code, 204)

    def test_delete_unknown_item(self):
        url = "/simpledoc/%s" % "abc"
        response = self.delete(url)
        self.assertEqual(response.status_code, 404)

    def test_delete_unknown_resource(self):
        response = self.delete("/unknown")
        self.assertEqual(response.status_code, 404)

    def test_delete_subresource_item(self):
        # create new resource and subresource
        s = SimpleDoc(a="Answer to everything", b=42).save()
        d = ComplexDoc(l=["a", "b"], n=999, r=s).save()

        response = self.client.get("/simpledoc/%s/complexdoc/%s" % (s.id, d.id))
        etag = response.get_json()[config.ETAG]
        headers = [("If-Match", etag)]

        # delete subresource
        del_url = "/simpledoc/%s/complexdoc/%s" % (s.id, d.id)
        response = self.client.delete(del_url, headers=headers)
        self.assertEqual(response.status_code, 204)
        # check, if really deleted
        response = self.client.get("/simpledoc/%s/complexdoc/%s" % (s.id, d.id))
        self.assertEqual(response.status_code, 404)
        s.delete()

    def test_delete_subresource(self):
        # more subresources -> delete them all
        s = SimpleDoc(a="James Bond", b=7).save()
        c1 = ComplexDoc(l=["p", "q", "r"], n=1, r=s).save()
        c2 = ComplexDoc(l=["s", "t", "u"], n=2, r=s).save()

        # delete subresources
        del_url = "/simpledoc/%s/complexdoc" % s.id
        response = self.client.delete(del_url)
        self.assertEqual(response.status_code, 204)
        # check, if really deleted
        response = self.client.get("/simpledoc/%s/complexdoc" % s.id)
        json_data = response.get_json()
        self.assertEqual(json_data[config.ITEMS], [])
        # cleanup
        s.delete()

    def test_reveres_delete_rule(self):
        now = get_utc_time()
        HawkeyDoc.objects.delete()
        h = HawkeyDoc(c=self._id, a="a", created_at=now, updated_at=now).save()

        # delete subresources
        url = "/simpledoc/%s" % self._id
        response = self.delete(url)
        self.assertEqual(response.status_code, 204)

        count = HawkeyDoc.objects.count()
        self.assertEqual(count, 0)

        # cleanup
        HawkeyDoc.objects.delete()


class TestHttpDeleteUsingSaveMethod(TestHttpDelete):
    @classmethod
    def setUpClass(cls):
        BaseTest.setUpClass()
        cls.app.data.mongoengine_options["use_document_delete_for_delete"] = True

    @classmethod
    def tearDownClass(cls):
        BaseTest.tearDownClass()
        cls.app.data.mongoengine_options["use_document_delete_for_delete"] = False
