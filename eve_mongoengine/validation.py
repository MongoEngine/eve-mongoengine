# -*- coding: utf-8 -*-

"""
    eve_mongoengine.validation
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    This module implements custom validator based on
    :class:`eve.io.mongo.validation`, which is cerberus-validator extension.

    The purpose of this module is to enable validation for special mongoengine
    fields.

    :copyright: (c) 2014 by Stanislav Heller.
    :license: BSD, see LICENSE for more details.
"""

from eve.io.mongo.validation import Validator
from flask import current_app as app
from mongoengine import ValidationError, FileField

from eve_mongoengine._compat import iteritems
from eve_mongoengine.utils import get_utc_time


class EveMongoengineValidator(Validator):
    """
    Helper validator which adapts mongoengine special-purpose fields
    to cerberus validator API.
    """

    def validate(self, document, schema=None, update=False, context=None):
        """
        Main validation method which simply tries to validate against cerberus
        schema and if it does not fail, repeats the same against mongoengine
        validation machinery.
        """

        # fix timestamp
        if app.config["DATE_CREATED"] in list(self.schema.keys()):
            now = get_utc_time()
            if not update:
                document[app.config["DATE_CREATED"]] = document.get(
                    app.config["DATE_CREATED"], now
                )
            document[app.config["LAST_UPDATED"]] = now

        # call default eve's validator
        if not Validator.validate(self, document, schema, update, context):
            return False

        # validate using mongoengine field validators
        if self.resource:
            model_cls = app.data.models[self.resource]
            translate = lambda x: model_cls._reverse_db_field_map.get(x)
            new_document = dict()
            for field, value in document.items():
                field_copy = field.split(".")
                field_copy[0] = translate(field_copy[0])
                if None not in field_copy:
                    new_document[".".join(field_copy)] = value
            document = new_document
            doc = model_cls(**document)
            # rewind all file-like's
            for attr, field in iteritems(model_cls._fields):
                if isinstance(field, FileField) and attr in document:
                    document[attr].stream.seek(0)
            try:
                doc.validate()
            except ValidationError as e:
                for field_name, error in e.errors.items():
                    self._error(field_name, str(e))
                return False

        return True

    def _validate_type_dynamic(self, field, value):
        """
        Dummy validation method just to convince cerberus not to validate that
        value.
        """
        pass
