
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

from .schema import create_schema
from .datalayer import MongoengineDataLayer


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
    """
    def __init__(self):
        self.data = None
        self.models = {}

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
        # now we can fix all models
        for model_cls in self.models.itervalues():
            self.fix_model_class(model_cls)
        # overwrite default data layer to get proper mongoengine functionality
        app.data = MongoengineDataLayer(self)

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
        settings = {}
        domain = settings['DOMAIN'] = {}
        if not isinstance(models, (list, tuple)):
            models = [models]
        for model_cls in models:
            if not issubclass(model_cls, mongoengine.Document):
                raise TypeError("Class '%s' is not a subclass of "
                                "mongoengine.Document." % model_cls.__name__)
            schema = create_schema(model_cls)
            resource_name = model_cls.__name__
            if lowercase:
                resource_name = resource_name.lower()
            domain[resource_name] = {'schema': schema}
            self.models[resource_name] = model_cls
        return settings

    def fix_model_class(self, model_cls):
        """
        Adds necessary fields (updated and created) into model class
        to ensure Eve's default functionality.

        This is a helper for correct manipulation with mongoengine documents
        within Eve. Eve needs 'updated' and 'created' fields for it's own
        purpose, but we cannot ensure that they are present in the model
        class. And even if they are, they may be of other field type or
        missbehave.

        :param model_cls: mongoengine's model class to be fixed up.
        """
        config = self.app.config
        try:
            last_updated = config.LAST_UPDATED
        except AttributeError:
            last_updated = 'updated'
        try:
            date_created = config.DATE_CREATED
        except AttributeError:
            date_created = 'created'
        date_utc = lambda: datetime.now().replace(microsecond=0)
        new_fields = {
            # TODO: updating last_updated field every time when saved
            last_updated: mongoengine.DateTimeField(default=date_utc),
            date_created: mongoengine.DateTimeField(default=date_utc)
        }
        for attr_name, attr_value in new_fields.iteritems():
            # If the field does exist, we just check if it has right
            # type (mongoengine.DateTimeField) and pass
            if attr_name in model_cls._fields:
                attr_value = model_cls._fields[attr_name]
                if not isinstance(attr_value, mongoengine.DateTimeField):
                    raise TypeError("Field '%s' is needed by Eve, but has "
                                    "wrong type '%s'." % (attr_name,
                                    attr_value.__class__.__name__))
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
            model_cls._fields_ordered = tuple(i[1] for i in sorted(
                                        (v.creation_counter, v.name)
                                        for v in model_cls._fields.itervalues()))

