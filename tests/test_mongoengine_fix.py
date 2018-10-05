
from datetime import datetime
import unittest

from mongoengine import Document, StringField, IntField

from eve.exceptions import SchemaException
from eve.utils import str_to_date, config
from eve_mongoengine import EveMongoengine

from tests import BaseTest, Eve, SimpleDoc, ComplexDoc, LimitedDoc, WrongDoc, SETTINGS
class TestMongoengineFix(unittest.TestCase):
    """
    Test fixing mongoengine classes for Eve's purposes.
    """
    def create_app(self, *models):
        app = Eve(settings=SETTINGS)
        app.debug = True
        ext = EveMongoengine(app)
        ext.add_model(models)
        return app

    def assertDateTimeAlmostEqual(self, d1, d2, precision='minute'):
        """
        Used for testing datetime, which cannot (or we do not want to) be
        injected into tested object. Omits second and microsecond part.
        """
        self.assertEqual(d1.year, d2.year)
        self.assertEqual(d1.month, d2.month)
        self.assertEqual(d1.day, d2.day)
        self.assertEqual(d1.hour, d2.hour)
        self.assertEqual(d1.minute, d2.minute)

    def _test_default_values(self, app, cls, updated_name='updated',
                             created_name='created'):
        # test updated and created fields if they are correctly generated
        with app.app_context():
            client = app.test_client()
            now = datetime.utcnow()
            d = cls(a="xyz", b=29)
            updated = getattr(d, updated_name)
            created = getattr(d, created_name)
            self.assertEqual(type(updated), datetime)
            self.assertEqual(type(created), datetime)
            self.assertDateTimeAlmostEqual(updated, now)
            self.assertDateTimeAlmostEqual(created, now)
            d.save()
            # test real returned values
            json_data = client.get('/simpledoc/').get_json()
            created_attr = app.config['DATE_CREATED']
            created_str = json_data[config.ITEMS][0][created_attr]
            date_created = str_to_date(created_str)
            self.assertDateTimeAlmostEqual(now, date_created)
            d.delete()

    def test_default_values(self):
        app = self.create_app(SimpleDoc)
        self.assertEqual(SimpleDoc._db_field_map['updated'], '_updated')
        self.assertEqual(SimpleDoc._reverse_db_field_map['_updated'], 'updated')
        self.assertEqual(SimpleDoc._db_field_map['created'], '_created')
        self.assertEqual(SimpleDoc._reverse_db_field_map['_created'], 'created')
        self._test_default_values(app, SimpleDoc)

    def test_wrong_doc(self):
        with self.assertRaises(TypeError):
            self.create_app(WrongDoc)

    def test_nondefault_last_updated_field(self):
        # redefine to get entirely new class
        class SimpleDoc(Document):
            a = StringField()
            b = IntField()
        sett = SETTINGS.copy()
        sett['LAST_UPDATED'] = 'last_change'
        app = Eve(settings=sett)
        app.debug = True
        ext = EveMongoengine(app)
        ext.add_model(SimpleDoc)
        self._test_default_values(app, SimpleDoc, updated_name='last_change')

    def test_nondefault_date_created_field(self):
        # redefine to get entirely new class
        class SimpleDoc(Document):
            a = StringField()
            b = IntField()
        sett = SETTINGS.copy()
        sett['DATE_CREATED'] = 'created_at'
        app = Eve(settings=sett)
        app.debug = True
        ext = EveMongoengine(app)
        ext.add_model(SimpleDoc)
        self._test_default_values(app, SimpleDoc, created_name='created_at')
