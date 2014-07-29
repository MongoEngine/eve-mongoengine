
import json
import uuid
import unittest

from eve.exceptions import SchemaException
from eve.utils import config

from tests import (BaseTest, Eve, SimpleDoc, ComplexDoc, Inner, LimitedDoc,
                   WrongDoc, FieldsDoc, PrimaryKeyDoc, SETTINGS)
from eve_mongoengine._compat import iteritems, long

class TestFields(BaseTest, unittest.TestCase):

    def tearDown(self):
        FieldsDoc.objects.delete()

    def _fixture_template(self, data_ok, expected=None, data_fail=None, msg=None):
        d = FieldsDoc(**data_ok).save()
        if expected is None:
            expected = data_ok
        response = self.client.get('/fieldsdoc')
        json_data = response.get_json()[config.ITEMS][0]
        try:
            for key, value in iteritems(expected):
                self.assertEqual(json_data[key], value)
        finally:
            d.delete()
        if not data_fail:
            return
        # post
        response = self.client.post('/fieldsdoc/',
                                    data=json.dumps(data_fail),
                                    content_type='application/json')
        json_data = response.get_json()
        self.assertEqual(json_data[config.STATUS], "ERR")
        self.assertEqual(json_data[config.ISSUES], msg)

    def test_url_field(self):
        self._fixture_template(data_ok={'a':'http://google.com'},
                               data_fail={'a':'foobar'},
                               msg={'a': "ValidationError (FieldsDoc:None) (Invalid"\
                                   " URL: foobar: ['a'])"})

    def test_email_field(self):
        self._fixture_template(data_ok={'b':'heller.stanislav@gmail.com'},
                               data_fail={'b':'invalid@email'},
                               msg={'b': "ValidationError (FieldsDoc:None) (Invalid"\
                                   " Mail-address: invalid@email: ['b'])"})

    def test_uuid_field(self):
        self._fixture_template(data_ok={'g': 'ddbec64f-3178-43ed-aee3-1455968f24ab'},
                               data_fail={'g': 'foo-bar-baz'},
                               msg={'g': "ValidationError (FieldsDoc:None) (Could "\
                                   "not convert to UUID: badly formed hexade"\
                                   "cimal UUID string: ['g'])"})

    def test_long_field(self):
        self._fixture_template(data_ok={'c': long(999)})

    def test_decimal_field(self):
        self._fixture_template(data_ok={'d': 10.34})

    def test_sortedlist_field(self):
        self._fixture_template(data_ok={'e':[4,1,8]}, expected={'e': [1,4,8]})

    def test_map_field(self):
        self._fixture_template(data_ok={'f': {'x': 'foo', 'y': 'bar'}},
                               data_fail={'f': {'x': 1}},
                               msg={'f': "ValidationError (FieldsDoc:None) "\
                                   "(x.StringField only accepts string "\
                                   "values: ['f'])"})


    def test_embedded_document_field(self):
        i = Inner(a="hihi", b=123)
        d = ComplexDoc(i=i)
        d.save()
        response = self.client.get('/complexdoc')
        json_data = response.get_json()[config.ITEMS][0]
        self.assertDictEqual(json_data['i'], {'a':"hihi", 'b':123})
        d.delete()
        # POST request
        response = self.client.post('/complexdoc/',
                                    data='{"i": {"a": "xaxa", "b":-555}}',
                                    content_type='application/json')
        self.assertEqual(response.get_json()[config.STATUS], "OK")

        response = self.client.get('/complexdoc')
        json_data = response.get_json()[config.ITEMS][0]
        self.assertDictEqual(json_data['i'], {'a':"xaxa", 'b':-555})

        ComplexDoc.objects[0].delete()
        response = self.client.post('/complexdoc/',
                                    data='{"i": {"a": "bar", "b": "baz"}}',
                                    content_type='application/json')
        json_data = response.get_json()
        self.assertEqual(json_data[config.STATUS], "ERR")
        self.assertIn('i', json_data[config.ISSUES])
        self.assertIn('b', json_data[config.ISSUES]['i'])
        self.assertEqual(json_data[config.ISSUES]['i']['b'], 'must be of integer type')

    def test_embedded_in_list(self):
        # that's a tuff one
        i1 = Inner(a="foo", b=789)
        i2 = Inner(a="baz", b=456)
        d = ComplexDoc(o=[i1, i2])
        d.save()
        response = self.client.get('/complexdoc')
        try:
            json_data = response.get_json()[config.ITEMS][0]
            self.assertListEqual(json_data['o'], [{'a':"foo", 'b':789},{'a':"baz", 'b':456}])
        finally:
            d.delete()

    def test_dynamic_field(self):
        d = ComplexDoc(n=789)
        d.save()
        response = self.client.get('/complexdoc')
        try:
            json_data = response.get_json()[config.ITEMS][0]
            self.assertEqual(json_data['n'], 789)
        finally:
            # cleanup
            d.delete()

    def test_dict_field(self):
        d = ComplexDoc(d={'g':'good', 'h':'hoorai'})
        d.save()
        response = self.client.get('/complexdoc')
        try:
            json_data = response.get_json()[config.ITEMS][0]
            self.assertDictEqual(json_data['d'], {'g':'good', 'h':'hoorai'})
        finally:
            # cleanup
            d.delete()

    def test_reference_field(self):
        s = SimpleDoc(a="samurai", b=911)
        s.save()
        d = ComplexDoc(r=s)
        d.save()
        response = self.client.get('/complexdoc')
        try:
            json_data = response.get_json()[config.ITEMS][0]
            self.assertEqual(json_data['r'], str(s.id))
        finally:
            # cleanup
            d.delete()
            s.delete()

    def test_db_field_name(self):
        # test if eve returns fields named like in db, not in python
        response = self.client.post('/fieldsdoc/',
                                    data='{"longFieldName": "hello"}',
                                    content_type='application/json')
        json_data = response.get_json()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(json_data[config.STATUS], "OK")
        response = self.client.get('/fieldsdoc')
        json_data = response.get_json()[config.ITEMS][0]
        self.assertIn('longFieldName', json_data)
        self.assertEqual(json_data['longFieldName'], "hello")
        FieldsDoc.objects.delete()
        # the same, but through mongoengine
        FieldsDoc(n="hi").save()
        response = self.client.get('/fieldsdoc')
        json_data = response.get_json()[config.ITEMS][0]
        self.assertIn('longFieldName', json_data)
        self.assertEqual(json_data['longFieldName'], "hi")

    def test_non_standard_field(self):
        # tests FancyStringField -> it should be considered as StringField
        _type = self.app.config['DOMAIN']['fieldsdoc']['schema']['o']['type']
        self.assertEqual(_type, 'string')
        self._fixture_template(data_ok={'o':'Apples and oranges'},
                               data_fail={'o': 1},
                               msg={'o': "must be of string type"})

    def test_custom_primary_key(self):
        # test case, when custom id_field (primary key) is set.
        # XXX: datalayer should handle this instead of relying on default _id,
        # but eve does not support it :(, we have to raise exception.
        with self.assertRaises(SchemaException):
            self.ext.add_model(PrimaryKeyDoc)
