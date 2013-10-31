
"""
    eve_mongoengine.schema
    ~~~~~~~~~~~~~~~~~~~~~~

    Mapping mongoengine field types to cerberus schema.

    :copyright: (c) 2013 by Stanislav Heller.
    :license: BSD, see LICENSE for more details.
"""


from mongoengine import (StringField, IntField, FloatField, BooleanField,
                         DateTimeField, ComplexDateTimeField, URLField,
                         EmailField, LongField, DecimalField, ListField,
                         EmbeddedDocumentField, SortedListField, DictField,
                         MapField, UUIDField, ObjectIdField, LineStringField,
                         GeoPointField, PointField, PolygonField, BinaryField,
                         ReferenceField, DynamicField)

_mongoengine_to_cerberus = {
    StringField: 'string',
    IntField: 'integer',
    FloatField: 'float',
    BooleanField: 'boolean',
    DateTimeField: 'datetime',
    ComplexDateTimeField: 'datetime',
    URLField: 'string',
    EmailField: 'string',
    LongField: 'integer',
    DecimalField: 'float',
    EmbeddedDocumentField: 'dict',
    ListField: 'list',
    SortedListField: 'list',
    DictField: 'dict',
    MapField: 'dict',
    UUIDField: 'string',
    ObjectIdField: 'objectid',
    LineStringField: 'dict',
    GeoPointField: 'list',
    PointField: 'dict',
    PolygonField: 'dict',
    BinaryField: 'string',
    ReferenceField: 'objectid'

    #NOT SUPPORTED:
    # FileField, ImageField, SequenceField
    # GenericEmbeddedDocumentField
}


def create_schema(model_cls, lowercase=True):
    """
    :param model_cls: Mongoengine model class, subclass of
                      :class:`mongoengine.Document`.
    :param lowercase: True if names of resource for model class has to be
                      treated as lowercase string of classname.
    """
    schema = {}
    for fname, field in model_cls._fields.items():
        if getattr(field, 'eve_field', False):
            # do not convert auto-added fields 'updated' and 'created'
            continue
        if fname in ('_id', 'id'):
            # default id field, do not insert it into schema
            continue
        schema[fname] = fdict = {}
        if field.__class__ in _mongoengine_to_cerberus:
            cerberus_type = _mongoengine_to_cerberus[field.__class__]
            fdict['type'] = cerberus_type
            if field.required:
                fdict['required'] = True
            if field.unique:
                fdict['unique'] = True
            if field.choices:
                fdict['allowed'] = field.choices
            if getattr(field, 'max_length', None) is not None:
                fdict['maxlength'] = field.max_length
            if getattr(field, 'min_length', None) is not None:
                fdict['minlength'] = field.min_length
            if getattr(field, 'max_value', None) is not None:
                fdict['max'] = field.max_value
            if getattr(field, 'min_value', None) is not None:
                fdict['min'] = field.min_value
            # special cases
            elif field.__class__ is ReferenceField:
                # create data_relation schema
                resource = field.document_type.__name__
                if lowercase:
                    resource = resource.lower()
                # FIXME: what if id is of other field name?
                fdict['data_relation'] = {
                    'resource': resource,
                    'field': '_id',
                    'embeddable': True
                }
        elif field.__class__ is DynamicField:
            fdict['allow_unknown'] = True
    return schema
