from datetime import datetime

from ._compat import iteritems


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
