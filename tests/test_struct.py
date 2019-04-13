import unittest
from copy import deepcopy

from eve import Eve
from mongoengine import Document, StringField, ListField, IntField

from eve_mongoengine.struct import Settings
from eve_mongoengine import EveMongoengine


class TestSettingsDict(unittest.TestCase):
    def setUp(self):
        self.d = Settings({
            'a': 1,
            'b': "hello",
            'c': [1,2,3],
            'd': {'x': 'y', 'y': 5},
            'e': {'q': [1,2,{'e':5}], 'w': {'r':'s', 't':'u'}}
        })
        self.g = dict(deepcopy(self.d))
    
    def check(self):
        self.assertDictEqual(self.d, self.g)

    def test_simple(self):
        self.d.update({'a': 2})
        self.g['a'] = 2
        self.check()
        self.d.update({'b': "cheers"})
        self.g['b'] = "cheers"
        self.check()

    def test_list(self):
        self.d.update({'c': [1,2,4]})
        self.g['c'] = [1,2,4]
        self.check()
        self.d.update({'c': 4})
        self.g['c'] = 4
        self.check()
        self.d.update({'e': {'q': [1,2]}})
        self.g['e']['q'] = [1,2]
        self.check()

    def test_dict(self):
        self.d.update({'d': {'x': 'z'}})
        self.g['d'] = {'x': 'z', 'y': 5}
        self.check()

    def test_nested_dict(self):
        self.d.update({'e': {'w': {'r': 5}}})
        self.g['e']['w']['r'] = 5
        self.check()


if __name__ == "__main__":
    unittest.main()
