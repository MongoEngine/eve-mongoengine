
import json
from eve import Eve
import unittest
from eve.utils import config
from eve_mongoengine import EveMongoengine
from tests import SimpleDoc, in_app_context

SETTINGS = {
    'MONGO_HOST': 'localhost',
    'MONGO_PORT': 27017,
    'MONGO_DBNAME': 'eve_mongoengine_test',
    'DOMAIN': {'eve-mongoengine': {}},
    'RESOURCE_METHODS': ['GET', 'POST', 'DELETE'],
    'ITEM_METHODS': ['GET', 'PATCH', 'PUT'],
    'VERSIONING': True
}

class BaseVersioningTest(object):
    @classmethod
    def setUpClass(cls):
        SETTINGS['DOMAIN'] = {'eve-mongoengine':{}}
        app = Eve(settings=SETTINGS)
        app.debug = True
        ext = EveMongoengine(app)
        ext.add_model(SimpleDoc, resource_methods=['GET', 'POST', 'DELETE'], 
            item_methods=['GET', 'PATCH', 'PUT', 'DELETE'])
        cls.ext = ext
        cls.client = app.test_client()
        cls.app = app

    @classmethod
    def tearDownClass(cls):
        # deletes the whole test database
        cls.app.data.conn.drop_database(SETTINGS['MONGO_DBNAME'])

class TestDataLayer(BaseVersioningTest, unittest.TestCase):

    # TODO: Currently it fails because versioning is not supported by eve-mongoengine

    @unittest.skip("Currently it fails")
    @in_app_context
    def test_versioning(self):
        response = self.client.post('/simpledoc/',
                                    data='{"a": "jimmy", "b": 23}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, 201)
        post_data = response.get_json()
        self.assertEqual(post_data[config.STATUS], "OK")


