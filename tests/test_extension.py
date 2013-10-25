
import json

from datetime import datetime
import unittest
from mongoengine import (connect, Document, StringField, IntField,
                         EmbeddedDocumentField, EmbeddedDocument,
                         DictField, UUIDField, DynamicField, DateTimeField)

from flask import Response as BaseResponse

from eve.exceptions import SchemaException
from eve.utils import str_to_date
from eve import Eve

from eve_mongoengine import EveMongoengine

SETTINGS = {
    'MONGO_HOST': 'localhost',
    'MONGO_PORT': 27017,
    'MONGO_DBNAME': 'eve_mongoengine_test'
}

class Response(BaseResponse):
    def get_json(self):
        if 'application/json' in self.mimetype:
            return json.loads(self.get_data())
        else:
            raise TypeError("Not an application/json response")

# inject new reponse class for testing
Eve.response_class = Response

class SimpleDoc(Document):
    a = StringField()
    b = IntField()

class Inner(EmbeddedDocument):
    a = StringField()
    b = IntField()

class ComplexDoc(Document):
    i = EmbeddedDocumentField(Inner)
    d = DictField()
    n = DynamicField() # should be omitted
    u = UUIDField(db_field='x')

class LimitedDoc(Document):
    a = StringField(required=True)
    b = StringField(unique=True)
    c = StringField(choices=['x', 'y', 'z'])
    d = StringField(max_length=10)
    e = StringField(min_length=10)

class WrongDoc(Document):
    updated = IntField() # this is bad


class TestEveMongoengine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        ext = EveMongoengine()
        settings = ext.create_settings([SimpleDoc, ComplexDoc, LimitedDoc])
        settings.update(SETTINGS)
        app = Eve(settings=settings)
        ext.init_app(app)
        cls.client = app.test_client()
        cls.app = app

    @classmethod
    def tearDownClass(cls):
        # deletes the whole test database
        cls.app.data.conn.drop_database(SETTINGS['MONGO_DBNAME'])

    def test_find_one(self):
        d = SimpleDoc(a='Tom', b=223).save()
        response = self.client.get('/simpledoc/%s' % d.id)
        # has to return one record
        json_data = response.get_json()
        self.assertIn('updated', json_data)
        self.assertIn('created', json_data)
        self.assertEqual(json_data['_id'], str(d.id))
        self.assertEqual(json_data['a'], 'Tom')
        self.assertEqual(json_data['b'], 223)
        d.delete()

    def test_find_one_projection(self):
        # XXX: this it not eve's standard!
        self.skipTest('Projection on one document not supported')
        d = SimpleDoc(a='Tom', b=223).save()
        response = self.client.get('/simpledoc/%s?projection={"a":1}' % d.id)
        # has to return one record
        json_data = response.get_json()
        self.assertIn('updated', json_data)
        self.assertIn('created', json_data)
        self.assertNotIn('b', json_data)
        self.assertEqual(json_data['_id'], str(d.id))
        self.assertEqual(json_data['a'], 'Tom')
        d.delete()

    def test_find_one_nonexisting(self):
        response = self.client.get('/simpledoc/abcdef')
        self.assertEqual(response.status_code, 404)
        

    def test_find_all(self):
        _all = []
        for data in ({'a': "Hello", 'b':1},
                     {'a': "Hi", 'b': 2},
                     {'a': "Seeya", 'b': 3}):
            d = SimpleDoc(**data).save()
            _all.append(d)
        response = self.client.get('/simpledoc')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        s = set([item['a'] for item in data['_items']])
        self.assertSetEqual(set(['Hello', 'Hi', 'Seeya']), s)
        # delete records
        for d in _all:
            d.delete()

    def test_find_all_projection(self):
        d = SimpleDoc(a='Tom', b=223).save()
        response = self.client.get('/simpledoc?projection={"a": 1}')
        self.assertNotIn('b', response.get_json()['_items'][0])
        d.delete()

    def test_find_all_pagination(self):
        self.skipTest("Not implemented yet.")

    def test_find_all_sorting(self):
        self.skipTest("Not implemented yet.")

    def test_find_all_filtering(self):
        self.skipTest("Not implemented yet.")

    def test_find_all_complex(self):
        self.skipTest("Not implemented yet")

    def test_uppercase_resource_names(self):
        self.skipTest("Not implemented yet")



class TestMongoengineFix(unittest.TestCase):
    """
    Test fixing mongoengine classes for Eve's purposes.
    """
    def create_app(self, *models):
        ext = EveMongoengine()
        settings = ext.create_settings(models)
        settings.update(SETTINGS)
        app = Eve(settings=settings)
        ext.init_app(app)
        return app.test_client()

    def assertDateTimeAlmostEqual(self, d1, d2, precission='minute'):
        """
        Used for testing datetime, which cannot (or we do not want to) be
        injected into tested object. Omits second and microsecond part.
        """
        self.assertEqual(d1.year, d2.year)
        self.assertEqual(d1.month, d2.month)
        self.assertEqual(d1.day, d2.day)
        self.assertEqual(d1.hour, d2.hour)
        self.assertEqual(d1.minute, d2.minute)

    def test_default_values(self):
        # test updated and created fields if they are correctly generated
        app = self.create_app(SimpleDoc)
        now = datetime.now()
        d = SimpleDoc(a="xyz", b=29)
        self.assertEqual(type(d.updated), datetime)
        self.assertEqual(type(d.created), datetime)
        self.assertDateTimeAlmostEqual(d.updated, now)
        self.assertDateTimeAlmostEqual(d.created, now)
        d.save()
        # test real returned values
        json_data = app.get('/simpledoc/').get_json()
        created_str = json_data['_items'][0]['created']
        date_created = str_to_date(created_str)
        self.assertDateTimeAlmostEqual(now, date_created)
        d.delete()

    def test_wrong_doc(self):
        with self.assertRaises(SchemaException):
            self.create_app(WrongDoc)

