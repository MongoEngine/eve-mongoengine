
"""
    schema
    ~~~~~~

    Mapping mongoengine field types to cerberus schema.

    :copyright: (c) 2013 by Stanislav Heller.
    :license: BSD, see LICENSE for more details.
"""


from mongoengine import *

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
    DecimalField: 'integer',
    EmbeddedDocumentField: 'dict',
    ListField: 'list',
    SortedListField: 'list',
    DictField: 'dict',
    MapField: 'dict',
    UUIDField: 'string',
    ObjectIdField: 'objectid'
    #GeoPointField ??
    #PointField ??
    #LineStringField ??
    #BinaryField ??
    #ReferenceField ?? dict? objectid?
    #FileField ??
    #ImageField ??
}

def create_schema(model_cls):
    """
    :param model_cls: Mongoengine model class, subclass of
                      :class:`mongoengine.Document`.
    """
    schema = {}
    for fname, field in model_cls._fields.iteritems():
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
    return schema
