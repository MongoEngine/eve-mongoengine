
"""
    eve_mongoengine.datalayer
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    This module implements eve's data layer which uses mongoengine models
    instead of direct pymongo access.

    :copyright: (c) 2014 by Stanislav Heller.
    :license: BSD, see LICENSE for more details.
"""

# builtin
import ast
import json
from uuid import UUID

# 3rd party
from flask import abort
import pymongo
from mongoengine import (DoesNotExist, EmbeddedDocumentField, DictField,
                         MapField, ListField, FileField)
from mongoengine.connection import get_db, connect

# eve
from eve.io.mongo import Mongo, MongoJSONEncoder
from eve.io.mongo.parser import parse, ParseError
from eve.utils import config, debug_error_message, validate_filters
from eve.exceptions import ConfigException

# Python3 compatibility
from ._compat import itervalues, iteritems


def _itemize(maybe_dict):
    if isinstance(maybe_dict, list):
        return maybe_dict
    elif isinstance(maybe_dict, dict):
        return iteritems(maybe_dict)
    else:
        raise TypeError("Wrong type to itemize. Allowed lists and dicts.")


class MongoengineJsonEncoder(MongoJSONEncoder):
    """
    Propretary JSON encoder to support special mongoengine's special fields.
    """
    def default(self, obj):
        if isinstance(obj, UUID):
            # rendered as a string
            return str(obj)
        else:
            # delegate rendering to base class method
            return super(MongoengineJsonEncoder, self).default(obj)


class MongoengineDataLayer(Mongo):
    """
    Data layer for eve-mongoengine extension.

    Most of functionality is copied from :class:`eve.io.mongo.Mongo`.
    """
    json_encoder_class = MongoengineJsonEncoder

    _structured_fields = (EmbeddedDocumentField, DictField, MapField)

    def __init__(self, ext):
        """
        Constructor.

        :param ext: instance of :class:`EveMongoengine`.
        """
        # get authentication info
        username = ext.app.config['MONGO_USERNAME']
        password = ext.app.config['MONGO_PASSWORD']
        auth = (username, password)
        if any(auth) and not all(auth):
            raise ConfigException('Must set both USERNAME and PASSWORD '
                                  'or neither')
        # try to connect to db
        self.conn = connect(ext.app.config['MONGO_DBNAME'],
                            host=ext.app.config['MONGO_HOST'],
                            port=ext.app.config['MONGO_PORT'])
        self.models = ext.models
        self.app = ext.app
        # create dummy driver instead of PyMongo, which causes errors
        # when instantiating after config was initialized
        self.driver = type('Driver', (), {})()
        self.driver.db = get_db()
        # authenticate
        if any(auth):
            self.driver.db.authenticate(username, password)

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
        projection = set(projection.keys())

        # strip special underscore prefixed attributes -> in mongoengine
        # they arent prefixed
        for attr in ('_id', '_created', '_updated'):
            if attr in projection:
                projection.remove(attr)
                projection.add(attr.lstrip('_'))
        # id has to be always there
        projection.add('id')
        model_cls = self._get_model_cls(resource)
        if self._structure_in_model(model_cls):
            # cannot be resolved by calling 'only()'. We have to call exclude()
            # on all non-projected fields
            all_fields = set(model_cls._reverse_db_field_map.keys())
            # _id cannot be resolvable (this happens if inheritance is on)
            all_fields.discard('_id')
            non_projected = all_fields - projection
            qry = qry.exclude(*non_projected)
        else:
            projection.discard('id')
            rev_map = model_cls._reverse_db_field_map
            projection = [rev_map[field] for field in projection]
            projection.append('id')
            qry = qry.only(*projection)
        return qry

    def _get_model_cls(self, resource):
        try:
            return self.models[resource]
        except KeyError:
            abort(404)

    def find(self, resource, req, sub_resource_lookup):
        """
        Seach for results and return feed of them.

        :param resource: name of requested resource as string.
        :param req: instance of :class:`eve.utils.ParsedRequest`.
        :param sub_resource_lookup: sub-resource lookup from the endpoint url.
        """
        qry = self._get_model_cls(resource).objects
        if req.max_results:
            qry = qry.limit(req.max_results)
        if req.page > 1:
            qry = qry.skip((req.page - 1) * req.max_results)

        client_projection = {}
        client_sort = {}
        spec = {}

        # TODO sort syntax should probably be coherent with 'where': either
        # mongo-like # or python-like. Currently accepts only mongo-like sort
        # syntax.
        # TODO should validate on unknown sort fields (mongo driver doesn't
        # return an error)
        if req.sort:
            client_sort = ast.literal_eval(req.sort)

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

        if sub_resource_lookup:
            spec.update(sub_resource_lookup)

        spec = self._mongotize(spec, resource)

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
        datasource, spec, projection, sort = self._datasource_ex(
            resource,
            spec,
            client_projection,
            client_sort)

        if sort:
            for field, direction in _itemize(sort):
                if direction < 0:
                    field = "-%s" % field
                qry = qry.order_by(field)

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
        # transform every field value to correct type for querying
        lookup = self._mongotize(lookup, resource)
        datasource, filter_, projection, _ = self._datasource_ex(resource,
                                                                 lookup)
        qry = self._get_model_cls(resource).objects

        if len(filter_) > 0:
            qry = qry.filter(__raw__=filter_)
        qry = self._projection(resource, projection, qry)
        try:
            doc = qry.as_pymongo().get()
            for attr, value in iteritems(dict(doc)):
                if isinstance(value, (list, dict)) and not value:
                    del doc[attr]
            return doc
        except DoesNotExist:
            return None

    def _doc_to_model(self, resource, doc):
        if '_id' in doc:
            doc['id'] = doc.pop('_id')
        cls = self._get_model_cls(resource)
        instance = cls(**doc)
        for attr, field in iteritems(cls._fields):
            # Inject GridFSProxy object into the instance for every FileField.
            # This is because the Eve's GridFS layer does not work with the
            # model object, but handles insertion in his own workspace. Sadly,
            # there's no way how to work around this, so we need to do this
            # special hack..
            if isinstance(field, FileField):
                if attr in doc:
                    proxy = field.get_proxy_obj(key=field.name,
                                                instance=instance)
                    proxy.grid_id = doc[attr]
                    instance._data[attr] = proxy
        return instance

    def insert(self, resource, doc_or_docs):
        """Called when performing POST request"""
        datasource, filter_, _, _ = self._datasource_ex(resource)
        try:
            if isinstance(doc_or_docs, list):
                ids = []
                for doc in doc_or_docs:
                    model = self._doc_to_model(resource, doc)
                    model.save(write_concern=self._wc(resource))
                    ids.append(model.id)
                    doc[config.ID_FIELD] = model.id
                return ids
            else:
                model = self._doc_to_model(resource, doc_or_docs)
                model.save(write_concern=self._wc(resource))
                doc_or_docs[config.ID] = model.id
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
        nopfx = lambda x: x.lstrip('_')
        return dict(("set__%s" % nopfx(k), v) for (k, v) in iteritems(updates))

    def update(self, resource, id_, updates):
        """Called when performing PATCH request."""
        try:
            # FIXME: filters?
            kwargs = self._transform_updates_to_mongoengine_kwargs(updates)
            qry = self._get_model_cls(resource).objects(id=id_)
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

    def remove(self, resource, lookup):
        """Called when performing DELETE request."""
        lookup = self._mongotize(lookup, resource)
        datasource, filter_, _, _ = self._datasource_ex(resource, lookup)

        try:
            model_cls = self._get_model_cls(resource)
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
