import json
from functools import wraps

import mongoengine.signals
from eve import Eve
from flask import Response as BaseResponse
from mongoengine import *

from eve_mongoengine import EveMongoengine, get_utc_time

SETTINGS = {
    "MONGO_HOST": "mongodb://localhost:27017/eve_mongoengine_test?w=1&journal=false",
    "MONGO_PORT": "",
    "MONGO_DBNAME": "eve_mongoengine_test",
    "DOMAIN": {"eve-mongoengine": {}},
    "MERGE_NESTED_DOCUMENTS": False,
    "RESOURCE_METHODS": ["GET", "POST", "DELETE"],
    "ITEM_METHODS": ["GET", "PATCH", "PUT"],
    # "LAST_UPDATED": "updated_at",
    # "DATE_CREATED": "created_at",
    # 'ID_FIELD': '_id'',
}


class Response(BaseResponse):
    def get_json(self):
        if "application/json" in self.mimetype:
            data = self.get_data()
            try:
                data = data.decode("utf-8")
            except UnicodeDecodeError:
                pass
            return json.loads(data)
        else:
            raise TypeError("Not an application/json response")


# inject new reponse class for testing
Eve.response_class = Response


class SimpleDoc(Document):
    meta = {"allow_inheritance": True}
    a = StringField()
    b = IntField()


class Inherited(SimpleDoc):
    c = StringField(db_field="C")
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
    c = StringField(choices=["x", "y", "z"])
    d = StringField(max_length=10)
    e = StringField(min_length=10)
    f = IntField(min_value=5, max_value=10)


class WrongDoc(Document):
    updated = IntField()  # this is bad name


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
    n = StringField(db_field="longFieldName")
    o = FancyStringField()
    p = FileField()


class PrimaryKeyDoc(Document):
    # special document for testing primary key
    abc = StringField(db_field="ABC", primary_key=True)
    x = IntField()


class NonStructuredDoc(Document):
    # special document with custom db_field but without
    # any structured field (listField, dictField etc.)
    new_york = StringField(db_field="NewYork")


class HawkeyDoc(Document):
    # document with save() hooked
    a = StringField(required=True)
    b = StringField()
    c = ReferenceField(SimpleDoc, reverse_delete_rule=CASCADE)
    created_at = DateTimeField(required=True)
    updated_at = DateTimeField(required=True)

    def validate(self, clean=True):
        now = get_utc_time()
        if not self.created_at:
            self.created_at = now
        self.updated_at = now
        return super().validate(clean)


def update_b(sender, document):
    document.b = document.a * 2  # 'a' -> 'aa'


mongoengine.signals.pre_save.connect(update_b, sender=HawkeyDoc)


class SensitiveInfoDoc(Document):
    eve_exclude_fields = ["password"]
    username = StringField()
    password = StringField()

    @staticmethod
    def on_fetched_item(response):
        response["extra_field"] = "a"

    @staticmethod
    def on_fetched_resource(response):
        for item in response["_items"]:
            item["extra_field"] = "a"


class BaseTest(object):
    @classmethod
    def setUpClass(cls):
        SETTINGS["DOMAIN"] = {"eve-mongoengine": {}}
        app = Eve(settings=SETTINGS)
        app.debug = True
        with app.app_context():
            ext = EveMongoengine(app)
            for Doc in (
                SimpleDoc,
                ComplexDoc,
                LimitedDoc,
                FieldsDoc,
                NonStructuredDoc,
                Inherited,
                SensitiveInfoDoc,
            ):
                ext.add_model(
                    Doc,
                    resource_methods=["GET", "POST", "DELETE"],
                    item_methods=["GET", "PATCH", "PUT", "DELETE"],
                )
            ext.add_model(SensitiveInfoDoc, resource_name="user")
            cls.ext = ext
            cls.client = app.test_client()
            cls.app = app

    @classmethod
    def tearDownClass(cls):
        # deletes the whole test database
        cls.app.data.conn.drop_database(SETTINGS["MONGO_DBNAME"])


def in_app_context(fn):
    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        with self.app.app_context():
            return fn(self, *args, **kwargs)

    return wrapper
