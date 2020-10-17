eve-mongoengine2
=====================

![CI](https://github.com/wangsha/eve-mongoengine/workflows/CI/badge.svg)
![PyPI](https://img.shields.io/pypi/v/eve-mongoengine2)
![PyPI - Downloads](https://img.shields.io/pypi/dm/eve-mongoengine2)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/eve-mongoengine2)
![GitHub issues](https://img.shields.io/github/issues/wangsha/eve-mongoengine)
![Libraries.io dependency status for GitHub repo](https://img.shields.io/librariesio/github/wangsha/eve-mongoengine)
![PyPI - License](https://img.shields.io/pypi/l/eve-mongoengine2)

This is an active fork of the original [Eve-Mongoengine](https://github.com/MongoEngine/eve-mongoengine)

Differences from the original repo:
* compatible with latest [eve](https://github.com/pyeve/eve) release.
* automatically integrate eve hooks with mongoengine methods. Inspired by a fork https://github.com/liuq/eve-mongoengine
* added capability to skip certain fields during schema construction.
* added capability to customize resource name.

[Eve-Mongoengine](http://eve-mongoengine.readthedocs.org/en/latest/) is an
[Eve](https://github.com/pyeve/eve) extension, which enables
Mongoengine ODM models to be used as eve schema. If you use mongoengine
in your application and simultaneously want to use eve, instead of writing schema
again in cerberus format, you can use this extension, which takes your mongoengine
models and auto-transforms it into creberus schema.

**Official documentation:** http://eve-mongoengine.readthedocs.org/en/latest/

Install
-------
Simple installation using pip:
`pip install eve-mongoengine2`

It loads all dependencies as well.

For development use virtualenv and editable copy of repisotory:
`pip install -e git+https://github.com/wangsha/eve-mongoengine#egg=eve-mongoengine`

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

Or, if you are setting up your data before Eve is initialized, as is the case with application factories: 

```
import mongoengine
from eve import Eve
from eve_mongoengine import EveMongoengine

ext = EveMongoengine()
...
# init application
app = Eve(settings=my_settings)

# init extension
ext.init_app(app)
...
```

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

**Skip sensitive fields and eve hooks integration**

You can mark the model with `eve_exclude_fields` to skip certain model fields during schema construction. If you define eve hooks in mongoengine document, it will be automatically integrated.
```python
class SensitiveInfoDoc(Document):
    eve_exclude_fields = ["password"]
    username = StringField()
    password = StringField()

    @staticmethod
    def on_fetched_item(response):
        response["extra_field"] = "a"

    @staticmethod
    def on_fetched_resource(response):
        for item in response["_items"]:
            item["extra_field"] = "a"
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

**No auto-updating `LAST_UPDATED` field without http request**

If you update your document using mongoengine model (i.e. by calling `save()`, the `updated` field
will NOT be automatically updated to current time. If you want this behavior, please implement
 the hook yourself. Example:
 ```python
class HawkeyDoc(Document):
    # document with save() hooked
    a = StringField(required=True)
    b = StringField()
    c = ReferenceField(SimpleDoc, reverse_delete_rule=CASCADE)
    created_at = DateTimeField(required=True)
    updated_at = DateTimeField(required=True)

    def validate(self, clean=True):
        now = get_utc_time()
        if not self.created_at:
            self.created_at = now
        self.updated_at = now
        return super().validate(clean)
```

**Warning**: Be aware, that when using `QuerySet.update()` method, `LAST_UPDATED` field *WILL NOT*
be updated!



Options for mongoengine
-----------------------
Every insert/update (POST, PUT) goes through mongoengine's `Document.save()` method,
but PATCH method uses as default method atomic `mongoengine.QuerySet.update_one()`.
So if you have some hook bound to `save()` method, you loose it in this way.
But you have an option to use `save()` method in `PATCH` requests in exchange
for one database fetch, so it is relatively slower. The same applies to insertion and deletion. If
 you want to use this feature, set this options in data layer::

    app = Eve()
    ext = EveMongoengine(app)
    #: this switches from using QuerySet.update_one() to Document.save()
    app.data.mongoengine_options['use_document_save_for_patch'] = True
    
    #: this switches from using  cls.objects.insert() to Document.save() for each document
    app.data.mongoengine_options['use_document_save_for_insert'] = True
    
    #: this switches from using  cls.objects(filter).delete() to Document.delete() for each document
    app.data.mongoengine_options['use_document_delete_for_delete'] = True
    
    ext.add_model(Person)


Skip sub resource registration
-----------------------
If you want to skip register sub-resources, set `REGISTER_SUB_RESOURCE=True` in settings.

Limitations
-----------

* You have to give Eve some dummy domain to shut him up. Without this he
  will complain about empty domain.
* You cannot use mongoengine's custom `primary_key` (because of Eve).
* Cannot use `GenericEmbeddedDocumentField and SequenceField`.
* You can use FileField (tested) and ImageField (not tested yet), but
  operation with files handles Eve's GridFS layer, not mongoengine's
  GridFSProxy!
* Tested only on python 3.7/3.8

