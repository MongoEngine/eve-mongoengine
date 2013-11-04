
from datetime import datetime
import unittest

from eve.exceptions import SchemaException
from eve.utils import str_to_date
from eve_mongoengine import EveMongoengine

from tests import BaseTest, Eve, SimpleDoc, ComplexDoc, LimitedDoc, WrongDoc, SETTINGS

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
        now = datetime.utcnow()
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

