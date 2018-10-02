
from datetime import datetime
import unittest
import json
import time

from eve.utils import str_to_date, config
from eve_mongoengine import EveMongoengine
from mongoengine import ValidationError

from tests import BaseTest, Eve, SimpleDoc, ComplexDoc, LimitedDoc, WrongDoc, SETTINGS

class TestDataLayer(unittest.TestCase):
    """
    Test mongoengine eve datalayer db access, which must be compatible with Eve's view.
    """
    def create_app(self, *models):
        app = Eve(settings=SETTINGS)
        app.debug = True
        ext = EveMongoengine(app)
        ext.add_model(models)
        return app

    def setUp(self):
        self.app = self.create_app(SimpleDoc, ComplexDoc, LimitedDoc)
        self._created = self.app.config['DATE_CREATED']
        self._updated = self.app.config['LAST_UPDATED']
        self._etag = self.app.config['ETAG']

    def tearDown(self):
        for model in SimpleDoc, ComplexDoc, LimitedDoc:
            model.drop_collection()

    # TODO: create meta-tests with all document types

    def test_extra_fields_are_in_db(self):
        doc = SimpleDoc(a='a', b=42)
        doc.save()
        data = doc.to_json()
        self.assertIn(self._created, data)
        self.assertIn(self._updated, data)
        self.assertIn(self._etag, data)
        doc.delete()

    def test_created_and_updated_match_at_creation(self):
        app = self.create_app(SimpleDoc)
        doc = SimpleDoc(a='a', b=42)
        doc.save()
        data = json.loads(doc.to_json())
        self.assertEqual(data[self._created], data[self._updated])
        doc.delete()

    def test_created_and_updated_do_not_match_after_update(self):
        app = self.create_app(SimpleDoc)
        doc = SimpleDoc(a='a', b=42)
        doc.save()
        print("DOC:", doc.to_json())
        etag = doc[self._etag.lstrip("_")]
        doc.b = 12
        doc.save()
        print("DOC2:", doc.to_json())
        data = json.loads(doc.to_json())
        self.assertEqual(data['b'], 12)
        self.assertNotEqual(data[self._created], data[self._updated])
        self.assertNotEqual(etag, data[self._etag])

        doc.delete()


  
