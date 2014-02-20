
from io import BytesIO
import base64
import unittest

from eve.utils import config
from eve import STATUS_OK, ID_FIELD, STATUS, STATUS_ERR, ISSUES, ETAG
from tests import (BaseTest, Eve, SimpleDoc, ComplexDoc, Inner, LimitedDoc,
                   WrongDoc, FieldsDoc, PrimaryKeyDoc, SETTINGS)
from eve_mongoengine._compat import iteritems


class TestMedia(BaseTest, unittest.TestCase):
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

        # send a file and a required, ordinary field with no issues
        data = {'p': (BytesIO(self.clean), 'test.txt'), 'o': 'hello'}             
        resp = self.client.post('/fieldsdoc/', data=data, headers={}) #self.headers)
        self.assertEqual(resp.status_code, 201)
        j = resp.get_json()
        self.assertEqual(j[STATUS], STATUS_OK)
        # compare original and returned data
        _id = j[ID_FIELD]
        self.assertMediaField(_id, self.encoded, self.clean)

    def assertMediaField(self, _id, encoded, clean):
        # GET the file at the item endpoint
        resp = self.client.get('/fieldsdoc/%s' % _id)
        j = resp.get_json()
        returned = j['p']
        # returned value is a base64 encoded string
        self.assertEqual(returned, encoded)
        # which decodes to the original file clean
        self.assertEqual(base64.decodestring(returned.encode()), clean)
