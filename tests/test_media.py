
from io import BytesIO
import base64
import unittest
from bson import ObjectId

import eve
from eve.utils import config
from eve import STATUS_OK, ID_FIELD, STATUS, STATUS_ERR, ISSUES, ETAG
from tests import (BaseTest, Eve, SimpleDoc, ComplexDoc, Inner, LimitedDoc,
                   WrongDoc, FieldsDoc, PrimaryKeyDoc, SETTINGS)
from eve_mongoengine._compat import iteritems


class TestMedia(BaseTest, unittest.TestCase):
    # This test is basically copied-out of eve and slightly
    # modificated for purpose of eve-mongoengine

    def setUp(self):
        self.headers= {'Content-Type': 'multipart/form-data'}
        # we want an explicit binary as Py3 encodestring() expects binaries.
        self.clean = b'my file contents'
        # encodedstring will raise a DeprecationWarning under Python3.3, but
        # the alternative encodebytes is not available in Python 2.
        self.encoded = base64.encodestring(self.clean).decode('utf-8')

    def test_post_media(self):
        # wrong file
        data = {'p': 'not a file'}
        resp = self.client.post('/fieldsdoc/', data=data, headers=self.headers)
        j = resp.get_json()
        self.assertEqual(j[STATUS], STATUS_ERR)
        self.assertTrue('file was expected' in j[ISSUES]['p'])

        resp = self._post()
        self.assertEqual(resp.status_code, 201)
        j = resp.get_json()
        self.assertEqual(j[STATUS], STATUS_OK)
        # compare original and returned data
        _id = j[ID_FIELD]
        self.assertMediaField(_id, self.encoded, self.clean)

        # GET the file at the resource endpoint
        where = 'where={"%s": "%s"}' % (ID_FIELD, _id)
        resp = self.client.get('/fieldsdoc/?%s' % where)
        r = resp.get_json()
        self.assertEqual(len(r['_items']), 1)
        returned = r['_items'][0]['p']

        # returned value is a base64 encoded string
        self.assertEqual(returned, self.encoded)

        # which decodes to the original clean
        self.assertEqual(base64.decodestring(returned.encode()), self.clean)

    @unittest.skipIf(eve.__version__ == '0.4', "Fixed in eve 0.5")
    def test_put_media(self):
        resp = self._post()
        r = resp.get_json()
        _id = r[ID_FIELD]
        etag = r[ETAG]

        # retrieve media_id and compare original and returned data
        self.assertMediaField(_id, self.encoded, self.clean)

        media_id = self.assertMediaStored(_id)

        # PUT replaces the file with new one
        clean = b'my new file contents'
        encoded = base64.encodestring(clean).decode()
        data = {'p': (BytesIO(clean), 'test.txt'), 'o': 'byebye'}
        headers = [('Content-Type', 'multipart/form-data'), ('If-Match', etag)]

        resp = self.client.put('/fieldsdoc/%s' % _id, data=data, headers=headers)
        r = resp.get_json()
        self.assertEqual(STATUS_OK, r[STATUS])

        # compare original and returned data
        r = self.assertMediaField(_id, encoded, clean)

        # and of course, the ordinary field has been updated too
        self.assertEqual(r['o'], 'byebye')

        # previous media doesn't exist anymore (it's been deleted)
        self.assertFalse(self.app.media.exists(media_id))

    @unittest.skipIf(eve.__version__ == '0.4', "Fixed in eve 0.5")
    def test_patch_media(self):
        resp = self._post()
        r = resp.get_json()
        _id = r[ID_FIELD]
        etag = r[ETAG]

        # retrieve media_id and compare original and returned data
        self.assertMediaField(_id, self.encoded, self.clean)

        media_id = self.assertMediaStored(_id)

        # PATCH replaces the file with new one, but leaves ordinary field
        clean = b'my new file contents'
        encoded = base64.encodestring(clean).decode()
        data = {'p': (BytesIO(clean), 'test.txt')}
        headers = [('Content-Type', 'multipart/form-data'), ('If-Match', etag)]
        resp = self.client.patch('/fieldsdoc/%s' % _id, data=data, headers=headers)
        r = resp.get_json()
        self.assertEqual(STATUS_OK, r[STATUS])

        # compare original and returned data
        r = self.assertMediaField(_id, encoded, clean)

        # and of course, the ordinary field stays unchanged
        self.assertEqual(r['o'], 'hello')

        # previous media doesn't exist anymore (it's been deleted)
        self.assertFalse(self.app.media.exists(media_id))

    def test_media_delete(self):
        resp = self._post()
        r = resp.get_json()
        _id = r[ID_FIELD]
        etag = r[ETAG]

        # retrieve media_id and compare original and returned data
        self.assertMediaField(_id, self.encoded, self.clean)

        # DELETE deletes both the document and the media file
        headers = [('If-Match', etag)]

        resp = self.client.delete('/fieldsdoc/%s' % _id, headers=headers)
        self.assertEqual(resp.status_code, 200)

        # media doesn't exist anymore (it's been deleted)

        #self.assertFalse(self.app.media.exists(media_id))

        # GET returns 404
        resp = self.client.get('/fieldsdoc/%s' % _id)
        self.assertEqual(resp.status_code, 404)

    def assertMediaField(self, _id, encoded, clean):
        # GET the file at the item endpoint
        resp = self.client.get('/fieldsdoc/%s' % _id)
        self.assertEqual(resp.status_code, 200)
        j = resp.get_json()
        returned = j['p']
        # returned value is a base64 encoded string
        self.assertEqual(returned, encoded)
        # which decodes to the original file clean
        self.assertEqual(base64.decodestring(returned.encode()), clean)
        return j

    def assertMediaStored(self, _id):
        _db = self.app.data.driver.db
        # retrieve media id
        coll = FieldsDoc._get_collection_name()
        media_id = _db[coll].find_one({ID_FIELD: ObjectId(_id)})['p']
        # verify it's actually stored in the media storage system
        self.assertTrue(self.app.media.exists(media_id))
        return media_id

    def _post(self):
        # send a file and a required, ordinary field with no issues
        data = {'p': (BytesIO(self.clean), 'test.txt'), 'o': 'hello'}
        return self.client.post('/fieldsdoc/', data=data, headers=self.headers)

