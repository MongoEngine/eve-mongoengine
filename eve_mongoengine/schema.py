
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
    ObjectIdField: 'objectid',
    LineStringField: 'string'
    #GeoPointField ??
    #PointField ??
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
            if field.__class__ is EmbeddedDocumentField:
                # call recursively itself on embedded document to get schema
                fdict['schema'] = create_schema(field.document_type_obj)
        elif field.__class__ is DynamicField:
            fdict['allow_unknown'] = True
    return schema
