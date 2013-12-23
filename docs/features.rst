
Features
========

Main features:

* Auto-generated schema out of your mongoengine models
* Every operation goes through mongoengine -> you do not loose your mongoengine hooks
* Support for most of mongoengine fields (see `Limitations`_ for more info)
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

    {"_status": "ERR", "_issues": {'url': "ValidationError (Resource:None) (Invalid URL: not-an-url: ['url'])"}}


Advanced model registration
---------------------------
If you want to use the name of model class "as is", use option ``lowercase=False``
in ``add_model()`` method::

    ext.add_model(Person, lowercase=False)

Then you will have to ask the server for ``/Person/`` URL.

In ``add_model()`` method you can add every possible parameter into resource settings.
Even if you want to overwrite some settings, which generates eve-mongoengine under the hood,
you can overwrite it this way::

    ext.add_model(Person,                                       # model or models
                  resource_methods=['GET'],                     # allow only GET
                  cache_control="max-age=600; must-revalidate") # set max-age

When you register more than one model at time, you need to encapsulate all models into list::

    ext.add_model([Person, Car, House, Dog])

**HTTP Methods**

By default, all HTTP methods are allowed for registered classes:

* resource methods: `GET, POST, DELETE`
* item methods: `GET, PATCH, PUT, DELETE`


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

    app = Eve()
    ext = EveMongoengine(app)
    ext.add_model(Person)

    # Note that in db there are attributes '_updated' and '_created'.
    # Mongoengine field names are without underscore prefix!
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


Limitations
-----------
* You have to give Eve some dummy domain to shut him up. Without this he
  will complain about empty domain.
* You cannot use mongoengine's custom ``primary_key`` (because of Eve).
* Cannot use ``GenericEmbeddedDocumentField, FileField, ImageField, SequenceField``.
* Tested only on python 2.7 and 3.3.
* If you update your document using mongoengine model (i.e. by calling ``save()``,
  the ``updated`` field wont be updated to current time. This is because there arent
  any hooks bound to ``save()`` or ``update()`` methods and I consider this evil.

