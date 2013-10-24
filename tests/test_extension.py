
from datetime import datetime
import unittest
from mongoengine import (connect, Document, StringField, IntField,
                         EmbeddedDocumentField, EmbeddedDocument,
                         DictField, UUIDField, DynamicField, DateTimeField)

from eve.exceptions import SchemaException
from eve import Eve

from eve_mongoengine import EveMongoengine

SETTINGS = {
    'MONGO_HOST': 'localhost',
    'MONGO_PORT': 27017,
    'MONGO_DBNAME': 'eve_mongoengine_test'
}

date_utc = lambda: datetime.utcnow().replace(microsecond=0)

class SimpleDoc(Document):
    a = StringField()
    b = IntField()
    t = DateTimeField(default=date_utc)

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
    c = StringField(choices=[])
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

    def test_get_simple(self):
        for data in ({'a': "Hello", 'b':1},
                     {'a': "Hi", 'b': 2},
                     {'a': "Seeya", 'b': 3}):
            d = SimpleDoc(**data).save()
        #print self.client.get('/simpledoc').get_data()

    def test_get_complex(self):
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


    def test_default_values(self):
        app = self.create_app(SimpleDoc)
        d = SimpleDoc(a="xyz", b=29)
        self.assertEqual(type(d.updated), datetime)
        self.assertEqual(type(d.created), datetime)

    def test_wrong_doc(self):
        with self.assertRaises(SchemaException):
            self.create_app(WrongDoc)

