
from datetime import datetime
import unittest
import json
import time

from eve.utils import str_to_date, config
from eve_mongoengine import EveMongoengine
from mongoengine import ValidationError

from tests import BaseTest, Eve, SimpleDoc, ComplexDoc, LimitedDoc, WrongDoc, SETTINGS, in_app_context

class TestDataLayer(BaseTest, unittest.TestCase):

    def setUp(self):
        self._created = self.app.config['DATE_CREATED']
        self._updated = self.app.config['LAST_UPDATED']
        self._etag = self.app.config['ETAG']

    def tearDown(self):
        for model in SimpleDoc, ComplexDoc, LimitedDoc:
            model.drop_collection()

    # TODO: create meta-tests with all document types

    @in_app_context
    def test_extra_fields_are_in_db(self):
        doc = SimpleDoc(a='a', b=42)
        doc.save()
        data = doc.to_json()
        self.assertIn(self._created, data)
        self.assertIn(self._updated, data)
        self.assertIn(self._etag, data)
        doc.delete()

    @in_app_context
    def test_created_and_updated_match_at_creation(self):
        doc = SimpleDoc(a='a', b=42)
        doc.save()
        data = json.loads(doc.to_json())
        self.assertEqual(data[self._created], data[self._updated])
        doc.delete()

    @in_app_context
    def test_created_and_updated_do_not_match_after_update(self):
        doc = SimpleDoc(a='a', b=42)
        doc.save()
        etag = doc[self._etag.lstrip("_")]
        doc.b = 12
        time.sleep(1)
        doc.save()
        data = json.loads(doc.to_json())
        self.assertEqual(data['b'], 12)
        self.assertNotEqual(data[self._created], data[self._updated])
        self.assertNotEqual(etag, data[self._etag])
        doc.delete()


  
