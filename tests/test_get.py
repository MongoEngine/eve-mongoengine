import uuid
import unittest
from operator import attrgetter
from eve_mongoengine import EveMongoengine
from tests import (
    BaseTest,
    Eve,
    SimpleDoc,
    ComplexDoc,
    Inner,
    LimitedDoc,
    WrongDoc,
    NonStructuredDoc,
    Inherited,
    SETTINGS,
    SensitiveInfoDoc,
)


class TestHttpGet(BaseTest, unittest.TestCase):
    def test_find_one(self):
        d = SimpleDoc(a="Tom", b=223).save()
        response = self.client.get("/simpledoc/%s" % d.id)
        # has to return one record
        json_data = response.get_json()
        self.assertIn(self.app.config["LAST_UPDATED"], json_data)
        self.assertIn(self.app.config["DATE_CREATED"], json_data)
        self.assertEqual(json_data["_id"], str(d.id))
        self.assertEqual(json_data["a"], "Tom")
        self.assertEqual(json_data["b"], 223)
        d.delete()

    def test_find_one_projection(self):
        d = SimpleDoc(a="Tom", b=223).save()
        response = self.client.get('/simpledoc/%s?projection={"a":1}' % d.id)
        # has to return one record
        json_data = response.get_json()
        self.assertIn(self.app.config["LAST_UPDATED"], json_data)
        self.assertIn(self.app.config["DATE_CREATED"], json_data)
        self.assertNotIn("b", json_data)
        self.assertEqual(json_data["_id"], str(d.id))
        self.assertEqual(json_data["a"], "Tom")
        response = self.client.get('/simpledoc/%s?projection={"a":0}' % d.id)
        json_data = response.get_json()
        self.assertIn(self.app.config["LAST_UPDATED"], json_data)
        self.assertIn(self.app.config["DATE_CREATED"], json_data)
        self.assertIn("b", json_data)
        self.assertNotIn("a", json_data)
        self.assertEqual(json_data["_id"], str(d.id))
        d.delete()

    def test_find_one_nonexisting(self):
        response = self.client.get("/simpledoc/abcdef")
        self.assertEqual(response.status_code, 404)

    def test_projection_on_non_structured_doc(self):
        d = NonStructuredDoc(new_york="great").save()
        response = self.client.get("/nonstructureddoc/%s" % str(d.id))
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertIn("NewYork", json_data)
        self.assertEqual(json_data["NewYork"], "great")

    def test_datasource_projection(self):
        SETTINGS["DOMAIN"] = {"eve-mongoengine": {}}
        app = Eve(settings=SETTINGS)
        app.debug = True
        ext = EveMongoengine(app)
        ext.add_model(SimpleDoc, datasource={"projection": {"b": 0}})
        client = app.test_client()
        d = SimpleDoc(a="Tom", b=223).save()
        response = client.get("/simpledoc/%s" % d.id)
        try:
            self.assertNotIn("b", response.get_json().keys())
            # here it should return the field, but sadly, does not
            # response = client.get('/simpledoc/%s?projection={"b":1}' % d.id)
            # self.assertIn('b', response.get_json().keys())
        finally:
            d.delete()

    def test_find_all(self):
        _all = []
        for data in (
            {"a": "Hello", "b": 1},
            {"a": "Hi", "b": 2},
            {"a": "Seeya", "b": 3},
        ):
            d = SimpleDoc(**data).save()
            _all.append(d)
        response = self.client.get("/simpledoc")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        s = set([item["a"] for item in data["_items"]])
        self.assertSetEqual(set(["Hello", "Hi", "Seeya"]), s)
        # delete records
        for d in _all:
            d.delete()

    def test_find_all_projection(self):
        d = SimpleDoc(a="Tom", b=223).save()
        response = self.client.get('/simpledoc?projection={"a": 1}')
        self.assertNotIn("b", response.get_json()["_items"][0])
        response = self.client.get('/simpledoc?projection={"a": 1, "b": 1}')
        data = response.get_json()["_items"][0]
        self.assertIn("b", data)
        self.assertIn("a", data)
        response = self.client.get('/simpledoc?projection={"a": 0}')
        data = response.get_json()["_items"][0]
        self.assertIn("b", data)
        self.assertNotIn("a", data)
        d.delete()

    def test_find_all_pagination(self):
        self.skipTest("Not implemented yet.")

    def test_find_all_sorting(self):
        d = SimpleDoc(a="abz", b=3).save()
        d2 = SimpleDoc(a="abc", b=-7).save()
        response = self.client.get('/simpledoc?sort={"a":1}')
        json_data = response.get_json()
        real = [x["a"] for x in json_data["_items"]]
        expected = ["abc", "abz"]
        try:
            self.assertListEqual(real, expected)
        except Exception as e:
            # reset
            d.delete()
            d2.delete()
            raise

        response = self.client.get('/simpledoc?sort={"b":-1}')
        json_data = response.get_json()
        real = [x["b"] for x in json_data["_items"]]
        expected = [3, -7]
        try:
            self.assertListEqual(real, expected)
        finally:
            d.delete()
            d2.delete()

    def test_find_all_default_sort(self):
        s = self.app.config["DOMAIN"]["simpledoc"]["datasource"]
        d = SimpleDoc(a="abz", b=3).save()
        d2 = SimpleDoc(a="abc", b=-7).save()

        # set default sort to 'b', desc.
        if "default_sort" in s:
            default = s["default_sort"]
        else:
            default = []
        s["default_sort"] = [("b", -1)]
        self.app.set_defaults()
        response = self.client.get("/simpledoc")
        json_data = response.get_json()
        real = [x["b"] for x in json_data["_items"]]
        expected = [3, -7]
        try:
            self.assertListEqual(real, expected)
        except Exception as e:
            # reset
            s["default_sort"] = default
            d.delete()
            d2.delete()
            raise

        # set default sort to 'b', asc.
        s["default_sort"] = [("b", 1)]
        self.app.set_defaults()
        response = self.client.get("/simpledoc")
        json_data = response.get_json()
        real = [x["b"] for x in json_data["_items"]]
        expected = [-7, 3]
        try:
            self.assertListEqual(real, expected)
        finally:
            # reset
            s["default_sort"] = default
            d.delete()
            d2.delete()

    def test_find_all_filtering(self):
        d = SimpleDoc(a="x", b=987).save()
        d2 = SimpleDoc(a="y", b=123).save()
        response = self.client.get('/simpledoc?where={"a": "y"}')
        json_data = response.get_json()
        try:
            self.assertEqual(len(json_data["_items"]), 1)
            self.assertEqual(json_data["_items"][0]["b"], 123)
        finally:
            d.delete()
            d2.delete()

    def test_etag_in_item_and_resource(self):
        # etag of some entity has to be the same when fetching one item compared
        # to etag of part of feed (resource)
        d = ComplexDoc().save()
        feed = self.client.get("/complexdoc/").get_json()
        item = self.client.get("/complexdoc/%s" % d.id).get_json()
        try:
            self.assertEqual(
                feed[self.app.config["ITEMS"]][0][self.app.config["ETAG"]],
                item[self.app.config["ETAG"]],
            )
        finally:
            d.delete()

    def test_embedded_resource_serialization(self):
        s = SimpleDoc(a="Answer to everything", b=42).save()
        d = ComplexDoc(r=s).save()
        response = self.client.get('/complexdoc?embedded={"r":1}')
        json_data = response.get_json()
        expected = {"a": "Answer to everything", "b": 42}
        try:
            emb = json_data["_items"][0]["r"]
            self.assertEqual(emb["a"], expected["a"])
            self.assertEqual(emb["b"], expected["b"])
            self.assertIn(self.app.config["DATE_CREATED"], emb)
            self.assertIn(self.app.config["LAST_UPDATED"], emb)
        finally:
            d.delete()
            s.delete()

    def test_uppercase_resource_names(self):
        # test default lowercase
        response = self.client.get("/SimpleDoc")
        self.assertEqual(response.status_code, 404)
        # uppercase
        app = Eve(settings=SETTINGS)
        app.debug = True
        ext = EveMongoengine(app)
        ext.add_model(SimpleDoc, lowercase=False)
        client = app.test_client()
        d = SimpleDoc(a="Tom", b=223).save()
        response = client.get("/SimpleDoc/")
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        expected_url = json_data[self.app.config["LINKS"]]["self"]["href"]
        if ":" in expected_url:
            expected_url = "/" + "/".join(expected_url.split("/")[1:])
        self.assertEqual(expected_url, "SimpleDoc")
        # not lowercase when uppercase
        response = client.get("/simpledoc/")
        self.assertEqual(response.status_code, 404)

    def test_get_subresource(self):
        s = SimpleDoc(a="Answer to everything", b=42).save()
        d = ComplexDoc(l=["a", "b"], r=s).save()
        d2 = ComplexDoc(l=["c", "d"], r=s).save()
        response = self.client.get("/simpledoc/%s/complexdoc" % s.id)
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(len(json_data["_items"]), 2)
        real = [x["l"] for x in json_data["_items"]]
        self.assertEqual(real, [["a", "b"], ["c", "d"]])

    def test_inherited(self):
        # tests if inherited documents behave the same way
        i = Inherited(a="Answer", b=42, c="BarBaz").save()
        response = self.client.get("/inherited/%s/" % i.id)
        self.assertIn("C", response.get_json())
        self.assertEqual(response.status_code, 200)
        # cannot throw mongoengine.LookUpError!
        response = self.client.get("/inherited/")
        self.assertEqual(response.status_code, 200)

    def test_exclude_sensitive_info(self):
        SensitiveInfoDoc.objects.delete()
        SensitiveInfoDoc(username="Alex", password="changeme").save()
        response = self.client.get("/sensitiveinfodoc/")
        items = response.json["_items"]
        self.assertNotIn("password", list(items[0].keys()))
        self.assertIn("extra_field", list(items[0].keys()))

        response = self.client.get('/sensitiveinfodoc/?projection={"password": 1}')
        items = response.json["_items"]
        self.assertNotIn("password", list(items[0].keys()))
        self.assertIn("extra_field", list(items[0].keys()))

        response = self.client.get("/sensitiveinfodoc/%s" % items[0]["_id"])
        item = response.json
        self.assertNotIn("password", list(item.keys()))
        self.assertIn("extra_field", list(item.keys()))

    def test_custom_resource_name(self):
        SensitiveInfoDoc.objects.delete()
        SensitiveInfoDoc(username="Alex", password="changeme").save()
        response = self.client.get("/user")
        items = response.json["_items"]
        self.assertTrue(len(items) > 0)
