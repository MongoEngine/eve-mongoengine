===============
Eve-MongoEngine
===============
:Info: Eve-MongoEngine provides MongoEngine integration with `Eve <http://python-eve.org/>`_.
:Repository: https://github.com/hellerstanislav/eve-mongoengine
:Author: Stanislav Heller (https://github.com/hellerstanislav)

.. image:: https://api.travis-ci.org/hellerstanislav/eve-mongoengine.png?branch=master
  :target: https://travis-ci.org/hellerstanislav/eve-mongoengine/
  
.. image:: https://requires.io/github/hellerstanislav/eve-mongoengine/requirements.png?branch=master
  :target: https://requires.io/github/hellerstanislav/eve-mongoengine/requirements/?branch=master

About
=====

Eve-MongoEngine is an `Eve`_ extension, which enables MongoEngine ODM  model to be used as an Eve / `Cerberus <https://github.com/nicolaiarocci/cerberus>`_ schema. This eliminates the need to re-write API schemas in the `Cerberus`_ format by using MongoEngine models to automatically export a corresponding Cerberus schema.

Additional documentation and examples can be found on `Read the Docs <http://eve-mongoengine.readthedocs.org/en/latest/>`_.

Installation
============

If you have ``pip`` installed you can use ``pip install eve-mongoengine``. Otherwise, you can download the
source from `GitHub <https://github.com/hellerstanislav/eve-mongoengine>`_ and run ``python
setup.py install``.

Dependencies
============

- Python 2.7+ or Python 3.3+

- eve>=0.5.3
- mongoengine>=0.8.7,<=0.9
- blinker


Optional Dependencies
---------------------

- *None*

Examples
========

A simple example of what Eve-MongoEngine code looks like:

.. code:: python

  import mongoengine
  from eve import Eve
  from eve_mongoengine import EveMongoengine

  # Example MongoEngine ODM Model
  class Person(mongoengine.Document):
      name = mongoengine.StringField()
      age = mongoengine.IntField()

  # Set up Eve Settings
  my_settings = {
      'MONGO_HOST': 'localhost',
      'MONGO_PORT': 27017,
      'MONGO_DBNAME': 'eve_mongoengine_test'
      'DOMAIN': {'eve-mongoengine': {}} # Must add a "Dummy" Domain for Eve
  }

  # Eve Initialization
  app = Eve(settings=my_settings)
  ext = EveMongoengine(app)
  # Register Models with Eve
  ext.add_model([Person,])
  
  # Start Eve
  app.run()


Validation
----------

By default, Eve validates against the Cerberus schema. With the Eve-MongoEngine extension, all validation is processed by Eve first (if possible) and then processed by the corresponding MongoEngine validation layer. If the MongoEngine validation layer throws an exception, it is caught and returned in the Cerberus error format.


Fields
------

Eve automatically maintains fields in the database named ``_updated`` and ``_created``. To maintain compatibility with Eve, Eve-MongoEngine automatically inserts MongoEngine fields called ``updated`` and ``created`` (with database names of ``_updated`` and ``_created`` respectively) into any registered models.


Options and Limitations
-----------------------

See more tuning options and current limitations on `Read the Docs`_.
