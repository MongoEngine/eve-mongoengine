eve-mongoengine
===============

Eve-Mongoengine is and [Eve](https://github.com/nicolaiarocci/eve/) extension, which
enables Mongoengine ODM models to be used as eve schema. If you use mongoengine
in your application and simultaneously want to use eve, instead of writing schema
again in cerberus format, you can use this extension, which takes your mongoengine
models and auto-transforms it into creberus schema.

*NOTE:* This extension depends on resolving eve's issue #146 (https://github.com/nicolaiarocci/eve/pull/146 - settings as dict).

Install
-------
Simple installation using pip:
`pip install eve-mongoengine`

It loads all dependencies as well.

For development use virtualenv and editable copy of repisotory:
`pip install -e git+https://github.com/hellerstanislav/eve-mongoengine#egg=eve-mongoengine`

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
Now the name of resource will be lowercase name of given class, in this example it will be
`person`, so the request could be `/person/`. If you want to use the name of model class
"as is", use option `lowercase=False` in `create_settings()` method:
```python
ext.create_settings(Person, lowercase=False)
```
Then you will have to ask the server for `/Person/` URL.

HTTP Methods
------------
By default, all HTTP methods are allowed for registered classes:
* resource methods: `GET, POST, DELETE`
* item methods: `GET, PATCH, PUT, DELETE`


Validation
----------
By default, eve validates against cerberus schema. Because mongoengine has larger scale
of validation possiblities, there are some cases, when eve does not recognize the validator
(for example mongoengine's `unique_with`), mongoengine raises exception and eve fails miserably
because of not catching this exception. If you hit this case, please, let me know and fill new issue.


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
ext.init_app(app)

Person._fields.keys() # equals ['name', 'age', 'updated', 'created']
```
If you already have these fields in your model, Eve will probably scream at you, that it's not
possible to have these fields in schema.
