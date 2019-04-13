
import json
from flask import Response as BaseResponse
from mongoengine import *
import mongoengine.signals
from eve import Eve
from functools import wraps

from eve_mongoengine import EveMongoengine

SETTINGS = {
    'MONGO_HOST': 'localhost',
    'MONGO_PORT': 27017,
    'MONGO_DBNAME': 'eve_mongoengine_test',
    'DOMAIN': {'eve-mongoengine': {}},
    'RESOURCE_METHODS': ['GET', 'POST', 'DELETE'],
    'ITEM_METHODS': ['GET', 'PATCH', 'PUT']
}

class Response(BaseResponse):
    def get_json(self):
        if 'application/json' in self.mimetype:
            data = self.get_data()
            try:
                data = data.decode('utf-8')
            except UnicodeDecodeError:
                pass
            json_data = json.loads(data)

            # Convert the special keys back to _prefix
            if 'id' in json_data:
                json_data['_id'] = json_data.pop('id')
            if 'created' in json_data:
                json_data['_created'] = json_data.pop('created')
            if 'updated' in json_data:
                json_data['_updated'] = json_data.pop('updated')
            if 'etag' in json_data:
                json_data['_etag'] = json_data.pop('etag')

            return json_data

        else:
            raise TypeError("Not an application/json response")

# inject new reponse class for testing
Eve.response_class = Response

class SimpleDoc(Document):
    meta = {
        'allow_inheritance': True
    }
    a = StringField()
    b = IntField()

class Inherited(SimpleDoc):
    c = StringField(db_field='C')
    d = DictField()

class Inner(EmbeddedDocument):
    a = StringField()
    b = IntField()

class ListInner(EmbeddedDocument):
    ll = ListField(StringField())

class ComplexDoc(Document):
    # more complex field with embedded documents and lists
    i = EmbeddedDocumentField(Inner)
    d = DictField()
    l = ListField(StringField())
    n = DynamicField()
    r = ReferenceField(SimpleDoc)
    o = ListField(EmbeddedDocumentField(Inner))
    p = ListField(EmbeddedDocumentField(ListInner))

class LimitedDoc(Document):
    # doc for testing field limits and properties
    a = StringField(required=True)
    b = StringField(unique=True)
    c = StringField(choices=['x', 'y', 'z'])
    d = StringField(max_length=10)
    e = StringField(min_length=10)
    f = IntField(min_value=5, max_value=10)
    g = StringField(choices=[
                    ['val1', 'test value 1'],
                    ('val2', 'test value 2'),
                    ['val3', 'test value 3']])

class WrongDoc(Document):
    updated = IntField() # this is bad name

class FancyStringField(StringField):
    pass

class FieldsDoc(Document):
    # special document for testing any other field types
    a = URLField()
    b = EmailField()
    c = LongField()
    d = DecimalField()
    e = SortedListField(IntField())
    f = MapField(StringField())
    g = UUIDField()
    h = ObjectIdField()
    i = BinaryField()

    j = LineStringField()
    k = GeoPointField()
    l = PointField()
    m = PolygonField()
    n = StringField(db_field='longFieldName')
    o = FancyStringField()
    p = FileField()

class PrimaryKeyDoc(Document):
    # special document for testing primary key
    abc = StringField(db_field='ABC', primary_key=True)
    x = IntField()

class NonStructuredDoc(Document):
    # special document with custom db_field but without
    # any structured field (listField, dictField etc.)
    new_york = StringField(db_field='NewYork')

class HawkeyDoc(Document):
    # document with save() hooked
    a = StringField()
    b = StringField()
    c = StringField()
    # and also cleaning
    def clean(self):
        self.c = 'Hello'

def update_b(sender, document):
    document.b = document.a * 2 # 'a' -> 'aa'
mongoengine.signals.pre_save.connect(update_b, sender=HawkeyDoc)


class BaseTest(object):
    @classmethod
    def setUpClass(cls):
        SETTINGS['DOMAIN'] = {'eve-mongoengine':{}}
        app = Eve(settings=SETTINGS)
        app.debug = True
        ext = EveMongoengine(app)
        for Doc in SimpleDoc, ComplexDoc, LimitedDoc, FieldsDoc, \
                       NonStructuredDoc, Inherited, HawkeyDoc:
            ext.add_model(Doc, resource_methods=['GET', 'POST', 'DELETE'], 
                item_methods=['GET', 'PATCH', 'PUT', 'DELETE'])
        cls.ext = ext
        cls.client = app.test_client()
        cls.app = app

    @classmethod
    def tearDownClass(cls):
        # deletes the whole test database
        cls.app.data.conn.drop_database(SETTINGS['MONGO_DBNAME'])

def in_app_context(fn):
    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        with self.app.app_context():
            return fn(self, *args, **kwargs)
    return wrapper