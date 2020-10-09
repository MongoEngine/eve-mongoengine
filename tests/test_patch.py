from bson import ObjectId
import json
import time
import unittest
from eve.utils import config
from tests import BaseTest, SimpleDoc, ComplexDoc, FieldsDoc


def post_simple_item(f):
    def wrapper(self):
        response = self.client.post(
            "/simpledoc/",
            data='{"a": "jimmy", "b": 23}',
            content_type="application/json",
        )
        json_data = response.get_json()
        self._id = json_data[config.ID_FIELD]
        self.url = "/simpledoc/%s" % self._id  # json_data[config.ID_FIELD]
        # response = self.client.get(self.url).get_json()
        self.etag = json_data[config.ETAG]
        self.updated = json_data[config.LAST_UPDATED]
        try:
            f(self)
        finally:
            SimpleDoc.objects().delete()

    return wrapper


def post_complex_item(f):
    def wrapper(self):
        payload = (
            '{"i": {"a": "hello"}, "d": {"x": null}, "l": ["m", "n"], '
            + '"o": [{"a":"hi"},{"b":9}], "p": [{"ll": ["q", "w"]}]}'
        )
        response = self.client.post(
            "/complexdoc/", data=payload, content_type="application/json"
        )
        json_data = response.get_json()
        self._id = json_data[config.ID_FIELD]
        self.url = "/complexdoc/%s" % json_data[config.ID_FIELD]
        self.etag = json_data[config.ETAG]
        # check if etags are okay
        self.assertEqual(self.client.get(self.url).get_json()[config.ETAG], self.etag)
        # self._id = response[config.ID_FIELD]
        self.updated = json_data[config.LAST_UPDATED]
        try:
            f(self)
        finally:
            ComplexDoc.objects().delete()

    return wrapper


class TestHttpPatch(BaseTest, unittest.TestCase):
    def do_patch(self, url=None, data=None, headers=None):
        if url is None:
            url = self.url
        if headers is None:
            headers = [("If-Match", self.etag)]
        return self.client.patch(
            url, data=data, content_type="application/json", headers=headers
        )

    def assert_correct_etag(self, patch_response):
        etag = patch_response.get_json()[config.ETAG]
        get_resp = self.client.get(self.url).get_json()

        get_etag = get_resp[config.ETAG]
        if etag != get_etag:
            print(get_resp)
            print(patch_response.get_json())

        self.assertEqual(etag, get_etag)

    @post_simple_item
    def test_patch_overwrite_all(self):
        patch_response = self.do_patch(data='{"a": "greg", "b": 300}')
        self.assert_correct_etag(patch_response)
        response = self.client.get(self.url).get_json()
        self.assertIn("a", response)
        self.assertEqual(response["a"], "greg")
        self.assertIn("b", response)
        self.assertEqual(response["b"], 300)

    @post_simple_item
    def test_patch_overwrite_subset(self):
        # test what was really updated
        raw = SimpleDoc._get_collection().find_one({"_id": ObjectId(self._id)})
        response = self.do_patch(data='{"a": "greg"}')
        self.assert_correct_etag(response)
        expected = dict(raw)
        expected["a"] = "greg"
        real = SimpleDoc._get_collection().find_one({"_id": ObjectId(self._id)})
        self.assertDictEqual(real, expected)
        # test if GET response returns corrent response
        response = self.client.get(self.url).get_json()
        self.assertIn("a", response)
        self.assertEqual(response["a"], "greg")
        self.assertIn("b", response)
        self.assertEqual(response["b"], 23)

    @post_complex_item
    def test_patch_dict_field(self):
        test = ComplexDoc.objects[0]
        self.assertListEqual(test.l, ["m", "n"])
        self.assertEqual(test.d["x"], None)
        self.assertEqual(test.i.a, "hello")
        # do PATCH
        response = self.do_patch(data='{"d": {"x": "789"}}')
        self.assert_correct_etag(response)
        real = ComplexDoc.objects[0]
        self.assertEqual(real.d["x"], "789")
        self.assertListEqual(real.l, ["m", "n"])
        self.assertEqual(real.i.a, "hello")

    @post_complex_item
    def test_patch_embedded_document(self):
        self.assertEqual(ComplexDoc.objects[0].i.a, "hello")
        response = self.do_patch(data='{"i": {"a": "bye"}}')
        self.assert_correct_etag(response)
        self.assertEqual(ComplexDoc.objects[0].i.a, "bye")

    @post_complex_item
    def test_patch_embedded_document_in_list(self):
        self.assertEqual(ComplexDoc.objects[0].o[0].a, "hi")
        self.assertEqual(len(ComplexDoc.objects[0].o), 2)
        response = self.do_patch(data='{"o": [{"a": "bye"}]}')
        self.assert_correct_etag(response)
        self.assertEqual(ComplexDoc.objects[0].o[0].a, "bye")
        self.assertEqual(len(ComplexDoc.objects[0].o), 1)

    @post_complex_item
    def test_patch_list(self):
        self.assertEqual(ComplexDoc.objects[0].l, ["m", "n"])
        # full one
        response = self.do_patch(data='{"l": ["n"]}')
        self.assert_correct_etag(response)
        self.etag = response.get_json()[config.ETAG]
        doc = ComplexDoc.objects[0]
        self.assertEqual(doc.l, ["n"])
        self.assertEqual(doc.i.a, "hello")

    '''
    etag has error
    @post_complex_item
    def test_patch_empty_list(self):
        """
        Sadly, in default mode (use_atomic_update_for_patch=True) this raises
        error and there is no way (except for patching eve) to workaround this
        without doing another mongo fetch (and break atomicity), which is the
        way how it is done.
        """
        # empty one
        response = self.do_patch(data='{"l": []}')
        self.assert_correct_etag(response)
        doc = ComplexDoc.objects[0]
        self.assertEqual(doc.l, [])
        self.assertEqual(doc.i.a, "hello")

    @post_complex_item
    def test_patch_empty_list_and_empty_dict(self):
        # https://github.com/NotSpecial/eve/commit/8ada989fe79156115e6af55b14b799b435f4de6a
        # empty one
        response = self.do_patch(data='{"l": [], "d": {}}')
        self.assert_correct_etag(response)
        doc = ComplexDoc.objects[0]
        self.assertEqual(doc.l, [])
        self.assertEqual(doc.d, {})
        self.assertEqual(doc.i.a, "hello")
    '''

    @post_complex_item
    def test_patch_list_in_list(self):
        self.assertEqual(ComplexDoc.objects[0].p[0].ll, ["q", "w"])
        response = self.do_patch(data='{"p": [{"ll": ["y"]}]}')
        self.assert_correct_etag(response)
        self.etag = response.get_json()[config.ETAG]
        doc = ComplexDoc.objects[0]
        self.assertEqual(doc.p[0].ll, ["y"])

    @post_complex_item
    def test_patch_empty_list_in_list(self):
        self.assertEqual(ComplexDoc.objects[0].p[0].ll, ["q", "w"])
        response = self.do_patch(data='{"p": [{"ll": []}]}')
        self.assert_correct_etag(response)
        self.etag = response.get_json()[config.ETAG]
        doc = ComplexDoc.objects[0]
        self.assertEqual(doc.p[0].ll, [])

    def test_patch_subresource(self):
        # create new resource and subresource
        s = SimpleDoc(a="Answer to everything", b=42).save()
        d = ComplexDoc(l=["a", "b"], n=999, r=s).save()

        response = self.client.get("/simpledoc/%s/complexdoc/%s" % (s.id, d.id))
        etag = response.get_json()[config.ETAG]
        headers = [("If-Match", etag)]

        # patch document
        patch_data = {"l": ["x", "y", "z"], "r": str(s.id)}
        patch_url = "/simpledoc/%s/complexdoc/%s" % (s.id, d.id)
        response = self.client.patch(
            patch_url,
            data=json.dumps(patch_data),
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
        self.assertEqual(json_data["n"], 999)

        # cleanup
        s.delete()
        d.delete()

    def test_patch_field_with_different_dbfield(self):
        # tests patching field whith has mongoengine's db_field specified
        # and different from python field name
        s = FieldsDoc(n="Hello").save()
        response = self.client.get("/fieldsdoc/%s" % s.id)
        etag = response.get_json()[config.ETAG]
        headers = [("If-Match", etag)]

        # patch document
        patch_data = {"longFieldName": "Howdy"}
        patch_url = "/fieldsdoc/%s" % s.id
        response = self.client.patch(
            patch_url,
            data=json.dumps(patch_data),
            content_type="application/json",
            headers=headers,
        )
        self.assertEqual(response.status_code, 200)
        resp_json = response.get_json()
        self.assertEqual(resp_json[config.STATUS], "OK")

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


class TestHttpPatchUsingSaveMethod(TestHttpPatch):
    @classmethod
    def setUpClass(cls):
        BaseTest.setUpClass()
        cls.app.data.mongoengine_options["use_atomic_update_for_patch"] = False

    @classmethod
    def tearDownClass(cls):
        BaseTest.tearDownClass()
        cls.app.data.mongoengine_options["use_atomic_update_for_patch"] = True
