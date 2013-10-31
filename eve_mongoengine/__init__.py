
"""
    eve_mongoengine
    ~~~~~~~~~~~~~~~

    This module implements Eve extension which enables Mongoengine models
    to be used as eve schema. If you use mongoengine in your application
    and simultaneously want to use eve, instead of writing schema again in
    cerberus format, you can use this extension, which takes your mongoengine
    models and auto-transforms it into creberus schema.

    :copyright: (c) 2013 by Stanislav Heller.
    :license: BSD, see LICENSE for more details.
"""

from datetime import datetime

import mongoengine

from .schema import SchemaMapper
from .datalayer import MongoengineDataLayer
from .struct import Settings
from .validation import EveMongoengineValidator
from ._compat import itervalues, iteritems

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# until eve#146 is fixed, we need this monkey-patch
from eve import Eve
import os
import sys


def _load_config(self):
    # load defaults
    self.config.from_object('eve.default_settings')
    if isinstance(self.settings, dict):
        self.config.update(self.settings)
    else:
        if os.path.isabs(self.settings):
            pyfile = self.settings
        else:
            abspath = os.path.abspath(os.path.dirname(sys.argv[0]))
            pyfile = os.path.join(abspath, self.settings)
        self.config.from_pyfile(pyfile)

    #overwrite settings with custom environment variable
    envvar = 'EVE_SETTINGS'
    if os.environ.get(envvar):
        self.config.from_envvar(envvar)
Eve.load_config = _load_config
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class EveMongoengine(object):
    """
    An extension to Eve which allows Mongoengine models to be registered
    as an Eve's "domain".

    Acts as Flask extension and implements its 'protocol'.

    Usage::

        from eve_mongoengine import EveMongoengine
        from eve import Eve

        my_default_settings = {'MONGO_DBNAME': 'test'}
        ext = EveMongoengine()
        settings = ext.create_settings([MyModel, MySuperModel])
        settings.update(my_default_settings)
        app = Eve(settings=settings)
        ext.init_app(app)

    This class tries hard to be extendable and hackable as possible, every
    possible value is either a method param (for IoC-DI) or class attribute,
    which can be overwriten in subclass.
    """
    #: Default HTTP methods allowed to manipulate with whole resources.
    #: These are assigned to settings of every registered model, if not given
    #: others.
    default_resource_methods = ['GET', 'POST', 'DELETE']

    #: Default HTTP methods allowed to manipulate with items (single records).
    #: These are assigned to settings of every registered model, if not given
    #: others.
    default_item_methods = ['GET', 'PATCH', 'PUT', 'DELETE']

    #: The class used as Eve validator, which is also one of Eve's constructor
    #: params. In EveMongoengine, we need to overwrite it. If extending, assign
    #: only subclasses of :class:`EveMongoengineValidator`.
    validator_class = EveMongoengineValidator

    #: Datalayer class - instance of this class is pushed to app.data attribute
    #: and Eve does it's magic. See :class`datalayer.MongoengineDataLayer` for
    #: more info.
    datalayer_class = MongoengineDataLayer

    #: The class used as settings dictionary. Usually subclass of dict with
    #: tuned methods/behaviour.
    settings_class = Settings

    #: Mapper from mongoengine model into cerberus schema. This class may be
    #: subclassed in the future to support new mongoenigne's fields.
    schema_mapper_class = SchemaMapper

    def __init__(self):
        self.models = {}

    def _get_date_func(self):
        """
        Returns function (or lambda) taking zero params and returning datetime
        instance. By default it is datetime.now() with correction of
        microseconds. Eve uses suprisingly datetime.utc_now(), which does not
        respect time zone.
        """
        return lambda: datetime.now().replace(microsecond=0)

    def _parse_config(self):
        # parse app config
        config = self.app.config
        try:
            self.last_updated = config.LAST_UPDATED
        except AttributeError:
            self.last_updated = 'updated'
        try:
            self.date_created = config.DATE_CREATED
        except AttributeError:
            self.date_created = 'created'

    def init_app(self, app):
        """
        Binds EveMongoengine extension to created eve application.

        Under the hood it fixes all registered models and overwrites default
        eve's datalayer :class:`eve.io.mongo.Mongo` into
        :class:`eve_mongoengine.datalayer.MongoengineDataLayer`.

        This method implements flask extension interface:
        :param app: eve application object, instance of :class:`eve.Eve`.
        """
        self.app = app
        # overwrite default eve.io.mongo.validation.Validator
        app.validator = self.validator_class
        self._parse_config()
        # now we can fix all models
        for model_cls in itervalues(self.models):
            self.fix_model_class(model_cls)
        # overwrite default data layer to get proper mongoengine functionality
        app.data = self.datalayer_class(self)

    def create_settings(self, models, lowercase=True):
        """
        Creates Eve settings for mongoengine model classes.

        Returns dict which has to be passed to the settings param in Eve's
        constructor.

        :param model: model or list of them (subclasses of
                      :class:`mongoengine.Document`).
        :param lowercase: if true, all class names will be taken lowercase as
                          resource names. Default True.
        """
        settings = self.settings_class({
            'RESOURCE_METHODS': list(self.default_resource_methods),
            'ITEM_METHODS': list(self.default_item_methods)
        })
        domain = settings['DOMAIN'] = {}
        if not isinstance(models, (list, tuple)):
            models = [models]
        for model_cls in models:
            if not issubclass(model_cls, mongoengine.Document):
                raise TypeError("Class '%s' is not a subclass of "
                                "mongoengine.Document." % model_cls.__name__)
            schema = self.schema_mapper_class.create_schema(model_cls,
                                                            lowercase)
            resource_name = model_cls.__name__
            if lowercase:
                resource_name = resource_name.lower()
            domain[resource_name] = {'schema': schema}
            self.models[resource_name] = model_cls
        return settings

    def fix_model_class(self, model_cls):
        """
        Internal method invoked during registering new model.

        Adds necessary fields (updated and created) into model class
        to ensure Eve's default functionality.

        This is a helper for correct manipulation with mongoengine documents
        within Eve. Eve needs 'updated' and 'created' fields for it's own
        purpose, but we cannot ensure that they are present in the model
        class. And even if they are, they may be of other field type or
        missbehave.

        :param model_cls: mongoengine's model class (instance of subclass of
                          `mongoengine.Document`) to be fixed up.
        """
        date_field_cls = mongoengine.DateTimeField
        date_func = self._get_date_func()
        new_fields = {
            # TODO: updating last_updated field every time when saved
            self.last_updated: date_field_cls(default=date_func),
            self.date_created: date_field_cls(default=date_func)
        }
        for attr_name, attr_value in iteritems(new_fields):
            # If the field does exist, we just check if it has right
            # type (mongoengine.DateTimeField) and pass
            if attr_name in model_cls._fields:
                attr_value = model_cls._fields[attr_name]
                if not isinstance(attr_value, mongoengine.DateTimeField):
                    info = (attr_name,  attr_value.__class__.__name__)
                    raise TypeError("Field '%s' is needed by Eve, but has"
                                    " wrong type '%s'." % info)
                continue
            # The way how we introduce new fields into model class is copied
            # out of mongoengine.base.DocumentMetaclass
            attr_value.name = attr_name
            if not attr_value.db_field:
                attr_value.db_field = attr_name
            # TODO: reverse-delete rules
            attr_value.owner_document = model_cls

            # now add a flag that this is automagically added field - it is
            # very useful when registering class more than once - create_schema
            # has to know, if it is user-added or auto-added field.
            attr_value.eve_field = True

            # now simulate DocumentMetaclass: add class attributes
            setattr(model_cls, attr_name, attr_value)
            model_cls._fields[attr_name] = attr_value
            model_cls._db_field_map[attr_name] = attr_name
            model_cls._reverse_db_field_map[attr_name] = attr_name

            # this is just copied from mongoengine and frankly, i just dont
            # have a clue, what it does...
            iterfields = itervalues(model_cls._fields)
            created = [(v.creation_counter, v.name) for v in iterfields]
            model_cls._fields_ordered = tuple(i[1] for i in sorted(created))
