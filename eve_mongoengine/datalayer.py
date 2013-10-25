
"""
    eve_mongoengine.datalayer
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    This module implements eve's data layer which uses mongoengine models
    instead of direct pymongo access.

    :copyright: (c) 2013 by Stanislav Heller.
    :license: BSD, see LICENSE for more details.
"""

import json

from bson.errors import InvalidId
from bson import ObjectId

from eve.io.mongo import Mongo
from eve.utils import config, debug_error_message, validate_filters, \
    str_to_date
from eve import ID_FIELD

from mongoengine import connect, DoesNotExist, EmbeddedDocumentField
import pymongo
from flask import abort


class MongoengineDataLayer(Mongo):
    """
    Data layer for eve-mongoengine extension.

    Most of functionality is copied from :class:`eve.io.mongo.Mongo`.
    """
    def __init__(self, ext):
        self.conn = connect(ext.app.config['MONGO_DBNAME'],
                            host=ext.app.config['MONGO_HOST'],
                            port=ext.app.config['MONGO_PORT'])
        self.models = ext.models
        self.app = ext.app

    def _projection(self, resource, projection, qry):
        """
        Ensures correct projection for mongoengine query.
        """
        if projection is None:
            return qry
        projection = set(projection.keys())
        if '_id' in projection:
            projection.remove('_id')

        # mongoengine's default id field name
        projection.add('id')
        qry = qry.only(*projection)

        # ensure inner fields of embedded documents to be loaded
        model_cls_fields = self.models[resource]._fields
        inner_fields = []
        for attr in projection:
            field = model_cls_fields.get(attr, None)
            if isinstance(field, EmbeddedDocumentField):
                for inner_attr in field.document_type_obj._fields.iterkeys():
                    inner_fields.append("%s.%s" % (attr, inner_attr))
        if inner_fields:
            qry = qry.only(*inner_fields)
        return qry


    def find(self, resource, req):
        """
        Seach for results and return feed of them.
        """
        qry = self.models[resource].objects
        args = dict()
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
            for field, direction in sort:
                if direction < 0:
                    field = "-%s" % field
                qry.order_by(field)

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
            except Exception, e:
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
        return self.models[resource](**doc)


    def insert(self, resource, doc_or_docs):
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

    def update(self, resource, id_, updates):
        raise NotImplementedError()

    def replace(self, resource, id_, document):
        raise NotImplementedError()

    def remove(self, resource, id_=None):
        raise NotImplementedError()

