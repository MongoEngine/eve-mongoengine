
import unittest
from mongoengine import Document, StringField, queryset_manager

from eve_mongoengine import EveMongoengine
from tests import Eve, SETTINGS, in_app_context


class TwoFaceDoc(Document):
    s = StringField()

    @queryset_manager
    def all_objects(self, queryset):
        return queryset.filter(s__nin=['a', 'b'])


class TestMongoengineFix(unittest.TestCase):
    """
    Test if non-standard querysets defined in datalayer work as expected.
    """

    @classmethod
    def setUpClass(cls):
        app = Eve(settings=SETTINGS)
        app.debug = True
        ext = EveMongoengine(app)
        ext.add_model(TwoFaceDoc)
        cls.app = app
        cls.client = app.test_client()

    @in_app_context
    def test_switch_queryset(self):
        t1 = TwoFaceDoc(s='x').save()
        t2 = TwoFaceDoc(s='a').save()
        t3 = TwoFaceDoc(s='b').save()
        t4 = TwoFaceDoc(s='abc').save()

        # set queryset to `all_objects`
        self.app.data.default_queryset = 'all_objects'
        r = self.client.get('/twofacedoc/').get_json()
        returned = set([x['s'] for x in r['_items']])
        self.assertSetEqual(set(['x', 'abc']), returned)

        # back to `objects`
        self.app.data.default_queryset = 'objects'
        r = self.client.get('/twofacedoc/').get_json()
        returned = set([x['s'] for x in r['_items']])
        self.assertSetEqual(set(['x', 'abc', 'a', 'b']), returned)