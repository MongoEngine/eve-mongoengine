
import uuid
import unittest
from tests import (BaseTest, Eve, SimpleDoc, ComplexDoc, Inner, LimitedDoc,
                   WrongDoc, FieldsDoc, SETTINGS)

class TestFieldTypes(BaseTest, unittest.TestCase):

    def test_url_field(self):
        d = FieldsDoc(a='http://google.com')
        d.save()
        response = self.client.get('/fieldsdoc')
        json_data = response.get_json()['_items'][0]
        self.assertEqual(json_data['a'], 'http://google.com')
        d.delete()
        # post
        response = self.client.post('/fieldsdoc/',
                                    data='{"a": "foobar"}',
                                    content_type='application/json')
        json_data = response.get_json()
        self.assertEqual(json_data['status'], "ERR")
        exp = "ValidationError (FieldsDoc:None) (Invalid URL: foobar: ['a'])"
        self.assertListEqual(json_data['issues'], [exp])


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

