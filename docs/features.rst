
Features
========

Main features:

* Auto-generated schema out of your mongoengine models
* Every operation goes through mongoengine -> you do not loose your mongoengine hooks
* Support for most of mongoengine fields (see Limitations for more info)
* Mongoengine validation layer not disconnected - use it as you wish

Validation
----------

By default, eve validates against cerberus schema. Because mongoengine has larger
scale of validation possiblities, there are some cases, when cerberus is not enough.
Eve-Mongoengine comes with fancy solution: all errors, which are catchable by cerberus,
are catched by cerberus and mongoengine ones are catched by custom validator and
returned in cerberus error format. Example of this case could be mongoengine's
URLField, which does not have it's cerberus opposie. In this case, if you fill
in wrong URL, you get mongoengine error message. Let's see an example with internet
resource as a model::

    class Resource(Document):
        url = URLField()
        author = StringField()

And then if you make POST request with wrong URL::

    $ curl -d '{"url": "not-an-url", "author": "John"}' -H 'Content-Type: application/json' http://my-eve-server/resource

The response will contain::

    {"status": "ERR", "issues": ["ValidationError (Resource:None) (Invalid URL: not-an-url: ['url'])"]}

About mongoengine fields
------------------------
Because Eve contains default functionality, which maintains fields 'updated' and 'created',
there has to be special hacky way how to do it in mongoengine too. At the time of
initializing EveMongoengine extension, all registered mongoengine classes get two
new fields: ``updated`` and ``created``, both type mongoengine.DateTimeField (of
course field names are taken from config values ``LAST_UPDATED`` and ``DATE_CREATED``.
This is is the only way how to ensure, that Eve will have these fields avaliable for
storing it's information about entity. So please, do not be surprised, that there
are two more fields in your model class::

    class Person(mongoengine.Document):
        name = mongoengine.StringField()
        age = mongoengine.IntField()

    ext = EveMongoengine()
    ... app init ...
    ext.init_app(app)

    Person._fields.keys() # equals ['name', 'age', 'updated', 'created']

If you already have these fields in your model, Eve will probably scream at you, that
it's not possible to have these fields in schema.


Mongoengine hooks
-----------------

If you use mongoengine hooks, you may be interested in what call is performed
when POSTing documents or what kind of call is being executed while
performing any other method from Eve's REST API. Here is the list you need:

============  ==========================
HTTP method   mongoengine's API call
============  ==========================
GET resource  :func:`QuerySet.filter()` + :func:`only(), exclude(), limit(), skip(), order_by()`
GET item      :func:`QuerySet.get()` (+ every filtering and
              limiting methods)
POST item     :func:`Document.save()`
PUT item      :func:`Document.save()`
PATCH item    :func:`QuerySet.update_one()` (atomic)
DELETE item   :func:`QuerySet.delete()`
============  ==========================

So if you have some hook bound to save() method, it should be executed every
POST and PUT call you make using Eve.
