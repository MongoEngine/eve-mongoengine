"""
    eve_mongoengine.schema
    ~~~~~~~~~~~~~~~~~~~~~~

    Mapping mongoengine field types to cerberus schema.

    :copyright: (c) 2014 by Stanislav Heller.
    :license: BSD, see LICENSE for more details.
"""

import copy

from eve.exceptions import SchemaException

# MongoEngine Fields
from mongoengine import (
    StringField,
    IntField,
    FloatField,
    BooleanField,
    DateTimeField,
    ComplexDateTimeField,
    URLField,
    EmailField,
    LongField,
    DecimalField,
    ListField,
    EmbeddedDocumentField,
    SortedListField,
    DictField,
    MapField,
    UUIDField,
    ObjectIdField,
    LineStringField,
    GeoPointField,
    PointField,
    PolygonField,
    BinaryField,
    ReferenceField,
    DynamicField,
    FileField,
    DynamicDocument,
)


class SchemaMapper(object):
    """
    Default mapper from mongoengine model classes into cerberus dict-like
    schema.
    """

    _mongoengine_to_cerberus = {
        StringField: "string",
        IntField: "integer",
        FloatField: "float",
        BooleanField: "boolean",
        DateTimeField: "datetime",
        ComplexDateTimeField: "datetime",
        URLField: "string",
        EmailField: "string",
        LongField: "integer",
        DecimalField: "float",
        EmbeddedDocumentField: "dict",
        ListField: "list",
        SortedListField: "list",
        DictField: "dict",
        MapField: "dict",
        UUIDField: "string",
        ObjectIdField: "objectid",
        LineStringField: "dict",
        GeoPointField: "list",
        PointField: "dict",
        PolygonField: "dict",
        BinaryField: "string",
        ReferenceField: "objectid",
        FileField: "media"
        # NOT SUPPORTED:
        # ImageField, SequenceField
        # GenericEmbeddedDocumentField
    }

    @classmethod
    def _resolve_field_class(cls, field):
        """
        Resolves field classes, which are non-standard (derived from existing
        ones) to get most of it's functionality.
        If no appropriate class is found for this field, returns DynamicField.
        """
        for klass in field.__class__.mro():
            if klass in cls._mongoengine_to_cerberus:
                return klass
        return DynamicField

    @classmethod
    def create_schema(cls, model_cls, lowercase=True):
        """
        :param model_cls: Mongoengine model class, subclass of
                        :class:`mongoengine.Document`.
        :param lowercase: True if names of resource for model class has to be
                        treated as lowercase string of classname.
        """
        schema = {}

        # A DynamicDocument in MongoEngine is an expandable / uncontrolled
        # schema type. Any data set against the DynamicDocument that is not a
        # pre-defined field is automatically converted to a DynamicField.
        if issubclass(model_cls, DynamicDocument):
            schema["allow_unknown"] = True

        for field in model_cls._fields.values():
            if field.primary_key:
                # defined custom primary key -> fail, cos eve doesnt support it
                raise SchemaException(
                    "Custom primary key not allowed - eve "
                    "does not support different id fields "
                    "for resources."
                )
            fname = field.db_field
            # validation
            if getattr(field, "eve_field", False):
                # Do not convert auto-added fields 'updated' and 'created'.
                # This attribute is injected into model in EveMongoengine's
                # fix_model_class() method.
                continue
            if fname in ("_id", "id", "_cls", "_types"):
                # default id field, do not insert it into schema
                # https://stackoverflow.com/questions/13824569/mongoengine-types-and-cls-fields
                continue
            if (
                hasattr(model_cls, "eve_exclude_fields")
                and fname in model_cls.eve_exclude_fields
            ):
                continue
            schema[fname] = cls.process_field(field, lowercase)
        return schema

    @classmethod
    def process_field(cls, field, lowercase):
        """
        Returns Eve field definition from Mongoengine field

        :param field: Mongoengine field
        :param lowercase: True if names of resource for model class has to be
                        treated as lowercase string of classname.
        """
        fdict = {}
        best_matching_cls = cls._resolve_field_class(field)

        if best_matching_cls in cls._mongoengine_to_cerberus:
            cerberus_type = cls._mongoengine_to_cerberus[best_matching_cls]
            fdict["type"] = cerberus_type

            # Allow null, which causes field to be deleted from db.
            # This cannot be fetched from field.null, because it would
            # cause allowance of nulls in db. We only want nulls in REST API.
            fdict["nullable"] = True

            if isinstance(field, EmbeddedDocumentField):
                fdict["schema"] = cls.create_schema(field.document_type)
            if isinstance(field, ListField):
                fdict["schema"] = cls.process_field(field.field, lowercase)

            if field.required:
                fdict["required"] = True
            if field.unique:
                fdict["unique"] = True
            if field.choices:
                allowed = []
                for choice in field.choices:
                    if isinstance(choice, (list, tuple)):
                        allowed.append(choice[0])
                    else:
                        allowed.append(choice)
                fdict["allowed"] = tuple(allowed)
            if getattr(field, "max_length", None) is not None:
                fdict["maxlength"] = field.max_length
            if getattr(field, "min_length", None) is not None:
                fdict["minlength"] = field.min_length
            if getattr(field, "max_value", None) is not None:
                fdict["max"] = field.max_value
            if getattr(field, "min_value", None) is not None:
                fdict["min"] = field.min_value

            # special cases
            if best_matching_cls is ReferenceField:
                # create data_relation schema
                resource = field.document_type.__name__
                if lowercase:
                    resource = resource.lower()
                fdict["data_relation"] = {
                    "resource": resource,
                    "field": "_id",
                    "embeddable": True,
                }

        elif best_matching_cls is DynamicField:
            fdict["type"] = "dynamic"

        return fdict

    @classmethod
    def get_subresource_settings(
        cls, model_cls, resource_name, resource_settings, lowercase=True
    ):
        """
        Yields name of subresource domain and it's settings.
        """
        for field in model_cls._fields.values():
            if field.__class__ is ReferenceField:
                fname = field.db_field
                subresource_settings = copy.deepcopy(resource_settings)
                subresource = field.document_type.__name__
                if lowercase:
                    subresource = subresource.lower()
                # FIXME what if id is of other type?
                _url = '%s/<regex("[a-f0-9]{24}"):%s>/%s'
                subresource_settings["url"] = _url % (subresource, fname, resource_name)
                yield subresource + resource_name, subresource_settings
