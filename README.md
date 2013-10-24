eve-mongoengine
===============

An Eve extension for Mongoengine ODM support.

*NOTE:* This extension depends on resolving eve's issue #146 (https://github.com/nicolaiarocci/eve/pull/146 - settings as dict).

Install
-------
Simple installation using pip:

```bash
pip install eve-mongoengine
```

It loads all dependencies as well.

For development use virtualenv and editable copy of repisotory:
```bash
pip install -e git+https://github.com/hellerstanislav/eve-mongoengine#egg=eve-mongoengine
```

Usage
-----
```python

import mongoengine
from eve import Eve
from eve_mongoengine import EveMongoengine

# create some dummy model class
class Person(mongoengine.Document):
    name = mongoengine.StringField()
    age = mongoengine.IntField()

# default eve settings
my_settings = {
    'MONGO_HOST': 'localhost',
    'MONGO_PORT': 27017,
    'MONGO_DBNAME': 'eve_mongoengine_test'
}

# at first init extension
ext = EveMongoengine()
# create schema from model class
settings = ext.create_settings(Person)
# merge model schema with settings
settings.update(my_settings)

# init application
app = Eve(settings=settings)
# do not forget to init extension!
ext.init_app(app)

# let's roll
app.run()

```

About mongoengine fields
------------------------
Because Eve contains default functionality, which maintains fields 'updated' and 'created',
there has to be special hacky way how to do it in mongoengine too. At the time of initializing
`EveMongoengine` extension, all registered mongoengine classes get two new fields: 'updated'
and 'created', both type `mongoengine.DateTimeField` (of course field names are taken from config
values `LAST_UPDATED` and `DATE_CREATED`. This is is the only way how to ensure, that
Eve will have these fields avaliable for storing it's information about entity.
So please, do not be surprised, that there are two more fields in your model class:
```python
class Person(mongoengine.Document):
    name = mongoengine.StringField()
    age = mongoengine.IntField()

ext = EveMongoengine()
... app init ...
extinit_app(app)

Person._fields.keys() # equals ['name', 'age', 'updated', 'created']
```
If you already have these fields in your model, Eve will probably scream at you, that it's not
possible to have these fields in schema.
