.. Eve-Mongoengine documentation master file, created by
   sphinx-quickstart on Fri Nov  1 09:05:09 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

:orphan:

Welcome to Eve-Mongoengine
==========================

Eve-Mongoengine is and Eve extension, which enables Mongoengine ODM models
to be used as eve schema. If you use mongoengine in your application and
simultaneously want to use eve, instead of writing schema again in cerberus
format, you can use this extension, which takes your mongoengine models and
auto-transforms it into creberus schema.

Contents:

.. toctree::
   :maxdepth: 1

   api


Install
-------

Simple installation using pip::

    pip install eve-mongoengine

It loads all dependencies as well (Eve and nothing more!).

For development use virtualenv and editable copy of repisotory::

    pip install -e git+https://github.com/hellerstanislav/eve-mongoengine#egg=eve-mongoengine


Usage
-----
::

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
    # do not forget to monkey-patch application!
    ext.init_app(app)

    # let's roll
    app.run()


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


