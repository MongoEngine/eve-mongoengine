eve-mongoengine 0.0.4
=====================

[![Build Status](https://travis-ci.org/hellerstanislav/eve-mongoengine.png?branch=master)](https://travis-ci.org/hellerstanislav/eve-mongoengine/)
[![Requirements Status](https://requires.io/github/hellerstanislav/eve-mongoengine/requirements.png?branch=master)](https://requires.io/github/hellerstanislav/eve-mongoengine/requirements/?branch=master)

[Eve-Mongoengine](http://eve-mongoengine.readthedocs.org/en/latest/) is an
[Eve](https://github.com/nicolaiarocci/eve/) extension, which enables
Mongoengine ODM models to be used as eve schema. If you use mongoengine
in your application and simultaneously want to use eve, instead of writing schema
again in cerberus format, you can use this extension, which takes your mongoengine
models and auto-transforms it into creberus schema.

**NOTE:** Initialization API has been changed since version 0.0.1! 

**Official documentation:** http://eve-mongoengine.readthedocs.org/en/latest/

Install
-------
Simple installation using pip:
`pip install eve-mongoengine`

It loads all dependencies as well.

For development use virtualenv and editable copy of repisotory:
`pip install -e git+https://github.com/hellerstanislav/eve-mongoengine#egg=eve-mongoengine`

Features
--------
* Auto-generated schema out of your mongoengine models
* Every operation goes through mongoengine -> you do not loose your mongoengine hooks
* Support for most of mongoengine fields (see [Limitations](#limitations) for more info)
* Support for your user-defined fields (as far as they are derived from some Mongoengine's non-base field)
* Mongoengine validation layer not disconnected - use it as you wish
* Partial support for eve's media - you can use ``FileField`` for this purpose (again see [Limitations](#limitations) for more info)

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
    'DOMAIN': {'eve-mongoengine': {}} # sadly this is needed for eve
}

# init application
app = Eve(settings=my_settings)
# init extension
ext = EveMongoengine(app)
# register model to eve
ext.add_model(Person)
# let's roll
app.run()
```
Now the name of resource will be lowercase name of given class, in this example it will be
`person`, so the request could be `/person/`.


Advanced model registration
---------------------------
If you want to use the name of model class "as is", use option `lowercase=False` in `add_model()` method:
```python
ext.add_model(Person, lowercase=False)
```
Then you will have to ask the server for `/Person/` URL.

In `add_model()` method you can add every possible parameter into resource settings.
Even if you want to overwrite some settings, which generates eve-mongoengine under the hood,
you can overwrite it this way:
```python
ext.add_model(Person,                                       # model or models
              resource_methods=['GET'],                     # allow only GET
              cache_control="max-age=600; must-revalidate") # set max-age
```
When you register more than one model at time, you need to encapsulate all models into list:
```python
ext.add_model([Person, Car, House, Dog])
```

**HTTP Methods**

By default, all HTTP methods are allowed for registered classes:
* resource methods: `GET, POST, DELETE`
* item methods: `GET, PATCH, PUT, DELETE`


Validation
----------
By default, eve validates against cerberus schema. Because mongoengine has larger scale
of validation possiblities, there are some cases, when cerberus is not enough. Eve-Mongoengine
comes with fancy solution: all errors, which are catchable by cerberus, are catched by cerberus
and mongoengine ones are catched by custom validator and returned in cerberus error format.
Example of this case could be mongoengine's `URLField`, which does not have it's cerberus
opposie. In this case, if you fill in wrong URL, you get mongoengine error message. Let's see
an example with internet resource as a model:
```python
class Resource(Document):
    url = URLField()
    author = StringField()
```
And then if you make POST request with wrong URL:
```
$ curl -d '{"url": "not-an-url", "author": "John"}' -H 'Content-Type: application/json' http://my-eve-server/resource
```
The response will contain
```
{"_status": "ERR", "_issues": {'url': "ValidationError (Resource:None) (Invalid URL: not-an-url: ['url'])"}}
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

app = Eve()
ext = EveMongoengine(app)
ext.add_model(Person)

Person._fields.keys() # equals ['name', 'age', 'updated', 'created']
```
If you already have these fields in your model, Eve will probably scream at you, that it's not
possible to have these fields in schema.

Limitations
-----------

* You have to give Eve some dummy domain to shut him up. Without this he
  will complain about empty domain.
* You cannot use mongoengine's custom `primary_key` (because of Eve).
* Cannot use `GenericEmbeddedDocumentField and SequenceField`.
* You can use FileField (tested) and ImageField (not tested yet), but
  operation with files handles Eve's GridFS layer, not mongoengine's
  GridFSProxy!
* Tested only on python 2.7 and 3.3.
* If you update your document using mongoengine model (i.e. by calling `save()`,
  the `updated` field wont be updated to current time. This is because there arent
  any hooks bound to `save()` or `update()` methods and I consider this evil.

