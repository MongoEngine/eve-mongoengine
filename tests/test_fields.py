
import json
import uuid
import unittest
from tests import (BaseTest, Eve, SimpleDoc, ComplexDoc, Inner, LimitedDoc,
                   WrongDoc, FieldsDoc, SETTINGS)

class TestFieldTypes(BaseTest, unittest.TestCase):

    def _fixture_template(self, data_ok, expected=None, data_fail=None, msg=None):
        d = FieldsDoc(**data_ok).save()
        if expected is None:
            expected = data_ok
        response = self.client.get('/fieldsdoc')
        json_data = response.get_json()['_items'][0]
        try:
            for key, value in expected.iteritems():
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
        self.assertEqual(json_data['status'], "ERR")
        self.assertListEqual(json_data['issues'], [msg])

    def test_url_field(self):
        self._fixture_template(data_ok={'a':'http://google.com'},
                               data_fail={'a':'foobar'},
                               msg="ValidationError (FieldsDoc:None) (Invalid"\
                                   " URL: foobar: ['a'])")

    def test_email_field(self):
        self._fixture_template(data_ok={'b':'heller.stanislav@gmail.com'},
                               data_fail={'b':'invalid@email'},
                               msg="ValidationError (FieldsDoc:None) (Invalid"\
                                   " Mail-address: invalid@email: ['b'])")

    def test_long_field(self):
        self._fixture_template(data_ok={'c': 999L})

    def test_decimal_field(self):
        self._fixture_template(data_ok={'d': 10.34})

    def test_sortedlist_field(self):
        self._fixture_template(data_ok={'e':[4,1,8]}, expected={'e': [1,4,8]})

    def test_map_field(self):
        self._fixture_template(data_ok={'f': {'x': 'foo', 'y': 'bar'}},
                               data_fail={'f': {'x': 1}},
                               msg="ValidationError (FieldsDoc:None) "\
                                   "(x.StringField only accepts string "\
                                   "values: ['f'])")


    def test_embedded_document_field(self):
        i = Inner(a="hihi", b=123)
        d = ComplexDoc(i=i)
        d.save()
        response = self.client.get('/complexdoc')
        json_data = response.get_json()['_items'][0]
        self.assertDictEqual(json_data['i'], {'a':"hihi", 'b':123})
        # cleanup
        d.delete()

    def test_dynamic_field(self):
        d = ComplexDoc(n=789)
        d.save()
        response = self.client.get('/complexdoc')
        json_data = response.get_json()['_items'][0]
        self.assertEqual(json_data['n'], 789)
        # cleanup
        d.delete()

    def test_dict_field(self):
        d = ComplexDoc(d={'g':'good', 'h':'hoorai'})
        d.save()
        response = self.client.get('/complexdoc')
        json_data = response.get_json()['_items'][0]
        self.assertDictEqual(json_data['d'], {'g':'good', 'h':'hoorai'})
        # cleanup
        d.delete()

    def test_reference_field(self):
        s = SimpleDoc(a="samurai", b=911)
        s.save()
        d = ComplexDoc(r=s)
        d.save()
        response = self.client.get('/complexdoc')
        json_data = response.get_json()['_items'][0]
        self.assertEqual(json_data['r'], str(s.id))
        # cleanup
        d.delete()
        s.delete()

