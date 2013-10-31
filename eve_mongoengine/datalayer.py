
"""
    eve_mongoengine.datalayer
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    This module implements eve's data layer which uses mongoengine models
    instead of direct pymongo access.

    :copyright: (c) 2013 by Stanislav Heller.
    :license: BSD, see LICENSE for more details.
"""

# builtin
import ast
import json

# 3rd party
from bson.errors import InvalidId
from bson import ObjectId
from flask import abort
import pymongo
from mongoengine import (connect, DoesNotExist, EmbeddedDocumentField,
                         DictField, MapField, ListField)

# eve
from eve.io.mongo import Mongo
from eve.io.mongo.parser import parse, ParseError
from eve.utils import config, debug_error_message, validate_filters
from eve import ID_FIELD

# Python3 compatibility
from ._compat import itervalues, iteritems


class MongoengineDataLayer(Mongo):
    """
    Data layer for eve-mongoengine extension.

    Most of functionality is copied from :class:`eve.io.mongo.Mongo`.
    """
    _structured_fields = (EmbeddedDocumentField, DictField, MapField)

    def __init__(self, ext):
        self.conn = connect(ext.app.config['MONGO_DBNAME'],
                            host=ext.app.config['MONGO_HOST'],
                            port=ext.app.config['MONGO_PORT'])
        self.models = ext.models
        self.app = ext.app

    def _structure_in_model(self, model_cls):
        """
        Returns True if model contains some kind of structured field.
        """
        for field in itervalues(model_cls._fields):
            if isinstance(field, self._structured_fields):
                return True
            elif isinstance(field, ListField):
                if isinstance(field.field, self._structured_fields):
                    return True
        return False

    def _projection(self, resource, projection, qry):
        """
        Ensures correct projection for mongoengine query.
        """
        if projection is None:
            return qry

        # fix mongoengine's 'id' field (_id -> id)
        projection = set(projection.keys())
        if '_id' in projection:
            projection.remove('_id')
        projection.add('id')

        model_cls = self.models[resource]
        if self._structure_in_model(model_cls):
            # cannot be resolved by calling 'only()'. We have to call exclude()
            # on all non-projected fields
            all_fields = set(model_cls._reverse_db_field_map.keys())
            non_projected = all_fields - projection
            qry = qry.exclude(*non_projected)
        else:
            qry = qry.only(*projection)
        return qry

    def find(self, resource, req):
        """
        Seach for results and return feed of them.
        """
        qry = self.models[resource].objects
        if req.max_results:
            qry = qry.limit(req.max_results)
        if req.page > 1:
            qry = qry.skip((req.page - 1) * req.max_results)

        # TODO sort syntax should probably be coherent with 'where': either
        # mongo-like # or python-like. Currently accepts only mongo-like sort
        # syntax.
        # TODO should validate on unknown sort fields (mongo driver doesn't
        # return an error)
        if req.sort:
            sort = ast.literal_eval(req.sort)
            for field, direction in iteritems(sort):
                if direction < 0:
                    field = "-%s" % field
                qry = qry.order_by(field)
        client_projection = {}
        spec = {}
        if req.where:
            try:
                spec = self._sanitize(json.loads(req.where))
            except:
                try:
                    spec = parse(req.where)
                except ParseError:
                    abort(400, description=debug_error_message(
                        'Unable to parse `where` clause'
                    ))
            spec = self._mongotize(spec)
        bad_filter = validate_filters(spec, resource)
        if bad_filter:
            abort(400, bad_filter)
        if req.projection:
            try:
                client_projection = json.loads(req.projection)
            except Exception as e:
                abort(400, description=debug_error_message(
                    'Unable to parse `projection` clause: '+str(e)
                ))
        datasource, spec, projection = self._datasource_ex(resource, spec,
                                                           client_projection)
        if req.if_modified_since:
            spec[config.LAST_UPDATED] = \
                {'$gt': req.if_modified_since}
        if len(spec) > 0:
            qry = qry.filter(__raw__=spec)
        qry = self._projection(resource, projection, qry)
        return qry.as_pymongo()

    def find_one(self, resource, **lookup):
        """
        Look for one object.
        """
        if config.ID_FIELD in lookup:
            try:
                lookup[ID_FIELD] = ObjectId(lookup[ID_FIELD])
            except (InvalidId, TypeError):
                # Returns a type error when {'_id': {...}}
                pass
        datasource, filter_, projection = self._datasource_ex(resource, lookup)
        qry = self.models[resource].objects
        if len(filter_) > 0:
            qry = qry.filter(__raw__=filter_)
        qry = self._projection(resource, projection, qry)
        try:
            return qry.as_pymongo().get()
        except DoesNotExist:
            return None

    def _doc_to_model(self, resource, doc):
        if '_id' in doc:
            doc['id'] = doc.pop('_id')
        return self.models[resource](**doc)

    def insert(self, resource, doc_or_docs):
        """Called when performing POST request"""
        datasource, filter_, _ = self._datasource_ex(resource)
        try:
            if isinstance(doc_or_docs, list):
                ids = []
                for doc in doc_or_docs:
                    model = self._doc_to_model(resource, doc)
                    model.save(write_concern=self._wc(resource))
                    ids.append(model.id)
                return ids
            else:
                model = self._doc_to_model(resource, doc_or_docs)
                model.save(write_concern=self._wc(resource))
                return model.id
        except pymongo.errors.OperationFailure as e:
            # most likely a 'w' (write_concern) setting which needs an
            # existing ReplicaSet which doesn't exist. Please note that the
            # update will actually succeed (a new ETag will be needed).
            abort(500, description=debug_error_message(
                'pymongo.errors.OperationFailure: %s' % e
            ))

    def _transform_updates_to_mongoengine_kwargs(self, updates):
        """
        Transforms update dict to special mongoengine syntax with set__,
        unset__ etc.
        """
        return dict((("set__%s" % k), v) for (k, v) in iteritems(updates))

    def update(self, resource, id_, updates):
        """Called when performing PATCH request."""
        try:
            # FIXME: filters?
            kwargs = self._transform_updates_to_mongoengine_kwargs(updates)
            qry = self.models[resource].objects(id=id_)
            qry.update_one(write_concern=self._wc(resource), **kwargs)
        except pymongo.errors.OperationFailure as e:
            # see comment in :func:`insert()`.
            abort(500, description=debug_error_message(
                'pymongo.errors.OperationFailure: %s' % e
            ))

    def replace(self, resource, id_, document):
        """Called when performing PUT request."""
        try:
            # FIXME: filters?
            model = self._doc_to_model(resource, document)
            model.save(write_concern=self._wc(resource))
        except pymongo.errors.OperationFailure as e:
            # see comment in :func:`insert()`.
            abort(500, description=debug_error_message(
                'pymongo.errors.OperationFailure: %s' % e
            ))

    def remove(self, resource, id_=None):
        """Called when performing DELETE request."""
        query = {ID_FIELD: ObjectId(id_)} if id_ else None
        datasource, filter_, _ = self._datasource_ex(resource, query)
        try:
            model_cls = self.models[resource]
            if not filter_:
                qry = model_cls.objects
            else:
                qry = model_cls.objects(__raw__=filter_)
            qry.delete(write_concern=self._wc(resource))
        except pymongo.errors.OperationFailure as e:
            # see comment in :func:`insert()`.
            abort(500, description=debug_error_message(
                'pymongo.errors.OperationFailure: %s' % e
            ))
