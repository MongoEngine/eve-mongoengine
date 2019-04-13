from ._compat import itervalues, iteritems
from datetime import datetime
from flask import current_app

def remove_eve_mongoengine_fields(doc, remove_fields=[]):
    if remove_fields == []:
        with current_app.app_context():
            remove_fields = [
                current_app.config.get('DATE_CREATED', '_created'), 
                current_app.config.get('LAST_UPDATED', '_updated'),
                current_app.config.get('ETAG', '_etag')
            ]
    for field in list(doc.keys()):
        if field.startswith('_') or field in set(remove_fields):
            doc.pop(field)
    return doc

def clean_doc(doc):
    """
    Cleans empty datastructures from mongoengine document (model instance)

    The purpose of this is to get proper etag.
    """
    for attr, value in iteritems(dict(doc)):
        if isinstance(value, (list, dict)) and not value:
            doc.pop(attr)
    return doc

def get_utc_time():
    """
    Returns current datetime in system-wide UTC format without microsecond
    part.
    """
    return datetime.utcnow().replace(microsecond=0)

def fix_underscore(field_name):
    return field_name.lstrip("_") if field_name.startswith("_") else field_name