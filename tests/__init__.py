
import json
from flask import Response as BaseResponse
from mongoengine import (connect, Document, StringField, IntField,
                         EmbeddedDocumentField, EmbeddedDocument,
                         DictField, UUIDField, DynamicField, DateTimeField,
                         ReferenceField, ListField)
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
    l = ListField(StringField())
    n = DynamicField()
    r = ReferenceField(SimpleDoc)
    #u = UUIDField(db_field='x') # Not supported by eve yet, see #102

class LimitedDoc(Document):
    a = StringField(required=True)
    b = StringField(unique=True)
    c = StringField(choices=['x', 'y', 'z'])
    d = StringField(max_length=10)
    e = StringField(min_length=10)
    f = IntField(min_value=5, max_value=10)

class WrongDoc(Document):
    updated = IntField() # this is bad


class BaseTest(object):
    @classmethod
    def setUpClass(cls):
        ext = EveMongoengine()
        settings = ext.create_settings([SimpleDoc, ComplexDoc, LimitedDoc])
        settings.update(SETTINGS)
        app = Eve(settings=settings)
        app.debug = True
        ext.init_app(app)
        cls.client = app.test_client()
        cls.app = app

    @classmethod
    def tearDownClass(cls):
        # deletes the whole test database
        cls.app.data.conn.drop_database(SETTINGS['MONGO_DBNAME'])

