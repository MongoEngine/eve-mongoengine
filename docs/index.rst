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

   features
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

    # init application
    app = Eve(settings=my_settings)
    # init extension
    ext = EveMongoengine(app)
    # register model to eve
    ext.add_model(Person)

    # let's roll
    app.run()

