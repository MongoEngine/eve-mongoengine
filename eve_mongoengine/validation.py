# -*- coding: utf-8 -*-

"""
    eve_mongoengine.validation
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    This module implements custom validator based on
    :class:`eve.io.mongo.validation`, which is cerberus-validator extension.

    The purpose of this module is to enable validation for special mongoengine
    fields.

    :copyright: (c) 2013 by Stanislav Heller.
    :license: BSD, see LICENSE for more details.
"""

from flask import current_app as app
from mongoengine import ValidationError

from eve.io.mongo.validation import Validator


class EveMongoengineValidator(Validator):
    """
    Helper validator which adapts mongoengine special-purpose fields
    to cerberus validator API.
    """
    def validate(self, document, schema=None, update=False):
        """
        Main validation method which simply tries to validate against cerberus
        schema and if it does not fail, repeats the same against mongoengine
        validation machinery.
        """
        if not Validator.validate(self, document, schema, update):
            return False
        model_cls = app.data.models[self.resource]
        doc = model_cls(**document)
        try:
            doc.validate()
        except ValidationError, e:
            self._error(str(e))
            return False
        return True
