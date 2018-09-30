"""
    eve_mongoengine
    ~~~~~~~~~~~~~~~

    This module implements Eve extension which enables Mongoengine models
    to be used as eve schema. If you use mongoengine in your application
    and simultaneously want to use eve, instead of writing schema again in
    cerberus format, you can use this extension, which takes your mongoengine
    models and auto-transforms it into creberus schema.

    :copyright: (c) 2014 by Stanislav Heller.
    :license: BSD, see LICENSE for more details.
"""

from datetime import datetime

import mongoengine

from .schema import SchemaMapper
from .datalayer import MongoengineDataLayer
from .struct import Settings
from .validation import EveMongoengineValidator
from ._compat import itervalues, iteritems


from .__version__ import get_version

__version__ = get_version()


def get_utc_time():
    """
    Returns current datetime in system-wide UTC format wichout microsecond
    part.
    """
    return datetime.utcnow().replace(microsecond=0)


class EveMongoengine(object):
    """
    An extension to Eve which allows Mongoengine models to be registered
    as an Eve's "domain".

    Acts as Flask extension and implements its 'protocol'.

    Usage::

        from eve_mongoengine import EveMongoengine
        from eve import Eve

        app = Eve()
        ext = EveMongoengine(app)
        ext.add_model([MyModel, MySuperModel])

    This class tries hard to be extendable and hackable as possible, every
    possible value is either a method param (for IoC-DI) or class attribute,
    which can be overwriten in subclass.
    """

    #: Default HTTP methods allowed to manipulate with whole resources.
    #: These are assigned to settings of every registered model, if not given
    #: others.
    default_resource_methods = ["GET"]

    #: Default HTTP methods allowed to manipulate with items (single records).
    #: These are assigned to settings of every registered model, if not given
    #: others.
    default_item_methods = ["GET"]

    #: The class used as Eve validator, which is also one of Eve's constructor
    #: params. In EveMongoengine, we need to overwrite it. If extending, assign
    #: only subclasses of :class:`EveMongoengineValidator`.
    validator_class = EveMongoengineValidator

    #: Datalayer class - instance of this class is pushed to app.data attribute
    #: and Eve does it's magic. See :class:`datalayer.MongoengineDataLayer` for
    #: more info.
    datalayer_class = MongoengineDataLayer

    #: The class used as settings dictionary. Usually subclass of dict with
    #: tuned methods/behaviour.
    settings_class = Settings

    #: Mapper from mongoengine model into cerberus schema. This class may be
    #: subclassed in the future to support new mongoenigne's fields.
    schema_mapper_class = SchemaMapper

    def __init__(self, app=None):
        self.models = {}
        if app is not None:
            self.init_app(app)

    def _parse_config(self):
        # parse app config
        config = self.app.config
        try:
            self.last_updated = config["LAST_UPDATED"]
        except KeyError:
            self.last_updated = "_updated"
        try:
            self.date_created = config["DATE_CREATED"]
        except KeyError:
            self.date_created = "_created"

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
        # overwrite default data layer to get proper mongoengine functionality
        app.data = self.datalayer_class(self)

    def _set_default_settings(self, settings):
        """
        Initializes default settings options for registered model.
        """
        if "resource_methods" not in settings:
            # TODO: maybe get from self.app.supported_resource_methods
            settings["resource_methods"] = list(self.default_resource_methods)
        if "item_methods" not in settings:
            # TODO: maybe get from self.app.supported_item_methods
            settings["item_methods"] = list(self.default_item_methods)

    def add_model(self, models, lowercase=True, **settings):
        """
        Creates Eve settings for mongoengine model classes.

        Returns dict which has to be passed to the settings param in Eve's
        constructor.

        :param model: model or list of them (subclasses of
                      :class:`mongoengine.Document`).
        :param lowercase: if true, all class names will be taken lowercase as
                          resource names. Default True.
        :param settings: any other keyword argument will be treated as param
                         to settings dictionary.
        """
        self._set_default_settings(settings)
        if not isinstance(models, (list, tuple)):
            models = [models]
        for model_cls in models:
            if not issubclass(model_cls, mongoengine.Document):
                raise TypeError(
                    "Class '%s' is not a subclass of "
                    "mongoengine.Document." % model_cls.__name__
                )

            resource_name = model_cls.__name__
            if lowercase:
                resource_name = resource_name.lower()

            # add new fields to model class to get proper Eve functionality
            self.fix_model_class(model_cls)
            self.models[resource_name] = model_cls

            schema = self.schema_mapper_class.create_schema(model_cls, lowercase)
            # create resource settings
            resource_settings = Settings({"schema": schema})
            resource_settings.update(settings)
            # register to the app
            self.app.register_resource(resource_name, resource_settings)
            # add sub-resource functionality for every ReferenceField
            subresources = self.schema_mapper_class.get_subresource_settings
            for registration in subresources(
                model_cls, resource_name, resource_settings, lowercase
            ):
                self.app.register_resource(*registration)
                self.models[registration[0]] = model_cls

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
                          :class:`mongoengine.Document`) to be fixed up.
        """
        date_field_cls = mongoengine.DateTimeField

        # field names have to be non-prefixed
        last_updated_field_name = self.last_updated.lstrip("_")
        date_created_field_name = self.date_created.lstrip("_")
        new_fields = {
            # TODO: updating last_updated field every time when saved
            last_updated_field_name: date_field_cls(
                db_field=self.last_updated, default=get_utc_time
            ),
            date_created_field_name: date_field_cls(
                db_field=self.date_created, default=get_utc_time
            ),
        }

        for attr_name, attr_value in iteritems(new_fields):
            # If the field does exist, we just check if it has right
            # type (mongoengine.DateTimeField) and pass
            if attr_name in model_cls._fields:
                attr_value = model_cls._fields[attr_name]
                if not isinstance(attr_value, mongoengine.DateTimeField):
                    info = (attr_name, attr_value.__class__.__name__)
                    raise TypeError(
                        "Field '%s' is needed by Eve, but has"
                        " wrong type '%s'." % info
                    )
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
            model_cls._db_field_map[attr_name] = attr_value.db_field
            model_cls._reverse_db_field_map[attr_value.db_field] = attr_name

            # this is just copied from mongoengine and frankly, i just dont
            # have a clue, what it does...
            iterfields = itervalues(model_cls._fields)
            created = [(v.creation_counter, v.name) for v in iterfields]
            model_cls._fields_ordered = tuple(i[1] for i in sorted(created))


def fix_last_updated(sender, document, **kwargs):
    """
    Hook which updates LAST_UPDATED field before every Document.save() call.
    """
    from eve.utils import config

    field_name = config.LAST_UPDATED.lstrip("_")
    if field_name in document:
        document[field_name] = get_utc_time()


mongoengine.signals.pre_save.connect(fix_last_updated)
