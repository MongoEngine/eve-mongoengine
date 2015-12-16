===============
Eve-MongoEngine
===============
:Info: Eve-MongoEngine provides MongoEngine integration with `Eve <http://python-eve.org/>`_.
:Repository: https://github.com/hellerstanislav/eve-mongoengine
:Author: Stanislav Heller (https://github.com/hellerstanislav)
:Maintainer: Matthew Ellison (https://github.com/seglberg)

----

.. |travis-master| image:: https://api.travis-ci.org/seglberg/eve-mongoengine.png?branch=master
  :target: https://travis-ci.org/seglberg/eve-mongoengine

.. |travis-develop| image:: https://api.travis-ci.org/seglberg/eve-mongoengine.png?branch=develop
  :target: https://travis-ci.org/seglberg/eve-mongoengine/branches

.. |landscape-master| image:: https://landscape.io/github/seglberg/eve-mongoengine/master/landscape.svg?style=flat
  :target: https://landscape.io/github/seglberg/eve-mongoengine/master
  :alt: Code Health

.. |landscape-develop| image:: https://landscape.io/github/seglberg/eve-mongoengine/develop/landscape.svg?style=flat
  :target: https://landscape.io/github/seglberg/eve-mongoengine/develop
  :alt: Code Health

.. list-table::
  :widths: 50 50
  :header-rows: 1

  * - Production
    - Development
  * - |travis-master|
    - |travis-develop|
  * - |landscape-master|
    - |landscape-develop|


**THE DEVELOP BRANCH CONTAINS POST-LEGACY WORK**

See the `legacy` tag for the last legacy release (0.0.10).

Do not use `develop` in production code. Instead, the `master` branch always points to the latest production release, and should be used instead.

.. warning::
    This branch or related tag is for a legacy version of the extension. Anything released before version 0.1 is considered legacy.

=======
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

Legacy Release
==============

The legacy version of the extension can be found under the 'legacy' tag. 
The legacy version of the extension was released under the BSD-2 license and originally authored by Stanislav Heller. See AUTHORS for more information about the legacy authors and ownership.
