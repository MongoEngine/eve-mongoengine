"""
    eve_mongoengine.datalayer
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    This module implements eve's data layer which uses mongoengine models
    instead of direct pymongo access.

    :copyright: (c) 2014 by Stanislav Heller.
    :license: BSD, see LICENSE for more details.
"""

# builtin
import sys
import ast
import json
from uuid import UUID
import traceback
from distutils.version import LooseVersion
from .utils import clean_doc

# --- Third Party ---

# MongoEngine
from mongoengine import __version__
from mongoengine import DoesNotExist, FileField
from mongoengine.connection import get_db, connect

MONGOENGINE_VERSION = LooseVersion(__version__)

# Eve
from eve.io.mongo import Mongo, MongoJSONEncoder
from eve.io.mongo.parser import parse, ParseError
from eve.utils import config, debug_error_message, validate_filters
from eve.exceptions import ConfigException

# Misc
from werkzeug.exceptions import HTTPException
from flask import abort, current_app as app
import pymongo

# Python3 compatibility
from ._compat import iteritems
from .utils import remove_eve_mongoengine_fields


def _itemize(maybe_dict):
    if isinstance(maybe_dict, list):
        return maybe_dict
    elif isinstance(maybe_dict, dict):
        return iteritems(maybe_dict)
    else:
        raise TypeError("Wrong type to itemize. Allowed lists and dicts.")


def dispatch_meta_properties(doc):
    extra = {}
    if hasattr(doc, '_meta_properties'):
        meta_properties = doc._meta_properties()
        for name, func in meta_properties.items():
            extra[name] = func()
    return extra

def check_permissions(doc, method):
    if hasattr(doc, '_check_permissions'):
        return doc._check_permissions(method)
    return True

class PymongoQuerySet(object):
    """
    Dummy mongoengine-like QuerySet behaving just like queryset
    with as_pymongo() called, but returning ALL fields in subdocuments
    (which as_pymongo() somehow filters).
    """

    def __init__(self, qs):
        self._qs = qs

    def __iter__(self):
        def iterate(obj):
            qs = object.__getattribute__(obj, "_qs")
            for doc in qs:
                extra = dispatch_meta_properties(doc)
                check_permissions(doc, 'GET')
                doc = dict(doc.to_mongo())
                doc[app.config.get('EVE_MONGOENGINE_EXTRA_FIELD', '_extra')] = extra
                for attr, value in iteritems(dict(doc)):
                    if isinstance(value, (list, dict)) and not value:
                        del doc[attr]
                yield doc

        return iterate(self)

    def __getattribute__(self, name):
        return getattr(object.__getattribute__(self, "_qs"), name)


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


class ResourceClassMap(object):
    """
    Helper class providing translation from resource names to mongoengine
    models and their querysets.
    """

    def __init__(self, datalayer):
        self.datalayer = datalayer

    def __getitem__(self, resource):
        try:
            return self.datalayer.models[resource]
        except KeyError:
            abort(404)

    def objects(self, resource):
        """
        Returns QuerySet instance of resource's class though mongoengine
        QuerySetManager. If there is some different queryset_manager
        defined in the MongoengineDataLayer class, it tries to use that one
        first.
        """
        _cls = self[resource]
        try:
            return getattr(_cls, self.datalayer.default_queryset)
        except AttributeError:
            # falls back to default `objects` QuerySet
            return _cls.objects


class MongoengineUpdater(object):
    """
    Helper class for managing updates (PATCH requests) through mongoengine
    ODM layer.

    Updates are managed in this class cecause sometimes things need to get
    drity and there would be unnecessary 'helper' methods in the main class
    MongoengineDataLayer causing namespace pollution.
    """

    def __init__(self, datalayer):
        self.datalayer = datalayer
        self._etag_doc = None
        self.install_etag_fixer()

    def install_etag_fixer(self):
        """
        Fixes ETag value returned by PATCH responses.
        """

    def _transform_updates_to_mongoengine_kwargs(self, resource, updates):
        """
        Transforms update dict to special mongoengine syntax with set__,
        unset__ etc.
        """
        field_cls = self.datalayer.cls_map[resource]
        nopfx = lambda x: field_cls._reverse_db_field_map[x]
        return dict(("set__%s" % nopfx(k), v) for (k, v) in iteritems(updates))

    def _has_empty_list_recurse(self, value):
        if value == []:
            return True
        if isinstance(value, dict):
            return self._has_empty_list(value)
        elif isinstance(value, list):
            for val in value:
                if self._has_empty_list_recurse(val):
                    return True
        return False

    def _has_empty_list(self, updates):
        """
        Traverses updates and returns True if there is update to empty list.
        """
        for key, value in iteritems(updates):
            if self._has_empty_list_recurse(value):
                return True
        return False

    def _update_document(self, doc, updates):
        """
        Makes appropriate calls to update mongoengine document properly by
        update definition given from REST API.
        """
        for db_field, value in iteritems(updates):
            field_name = doc._reverse_db_field_map[db_field]
            field = doc._fields[field_name]
            doc[field_name] = field.to_python(value)
        return doc

    def _update_using_save(self, resource, id_, updates):
        """
        Updates one document non-atomically using Document.save().
        """
        model = self.datalayer.cls_map.objects(resource)(id=id_).get()
        check_permissions(model, 'PATCH')
        self._update_document(model, updates)
        model.save(write_concern=self.datalayer._wc(resource))
        return model.etag

    def update(self, resource, id_, updates):
        """
        Resolves update for PATCH request.

        Does not handle mongo errors!
        """
        return self._update_using_save(resource, id_, updates)


class MongoengineDataLayer(Mongo):
    """
    Data layer for eve-mongoengine extension.

    Most of functionality is copied from :class:`eve.io.mongo.Mongo`.
    """

    #: default JSON encoder
    json_encoder_class = MongoengineJsonEncoder

    #: name of default queryset, where datalayer asks for data
    default_queryset = "objects"

    def __init__(self, ext):
        """
        Constructor.

        :param ext: instance of :class:`EveMongoengine`.
        """
        # get authentication info
        username = ext.app.config.get("MONGO_USERNAME", None)
        password = ext.app.config.get("MONGO_PASSWORD", None)
        auth = (username, password)
        if any(auth) and not all(auth):
            raise ConfigException("Must set both USERNAME and PASSWORD " "or neither")
        # try to connect to db
        self.conn = connect(
            ext.app.config["MONGO_DBNAME"],
            host=ext.app.config["MONGO_HOST"],
            port=ext.app.config["MONGO_PORT"],
        )
        self.models = ext.models
        self.app = ext.app
        # create dummy driver instead of PyMongo, which causes errors
        # when instantiating after config was initialized
        self.driver = type("Driver", (), {})()
        self.driver.db = get_db()
        # authenticate
        if any(auth):
            self.driver.db.authenticate(username, password)
        # helper object for managing PATCHes, which are a bit dirty
        self.updater = MongoengineUpdater(self)
        # map resource -> Mongoengine class
        self.cls_map = ResourceClassMap(self)

    def _handle_exception(self, exc):
        """
        If application is in debug mode, prints every traceback to stderr.
        """
        if self.app.debug:
            traceback.print_exc(file=sys.stderr)
        raise exc

    def _projection(self, resource, projection, qry):
        """
        Ensures correct projection for mongoengine query.
        """
        if projection is None:
            return qry

        model_cls = self.cls_map[resource]

        projection_value = set(projection.values())
        projection = set(projection.keys())

        # strip special underscore prefixed attributes -> in mongoengine
        # they arent prefixed
        projection.discard("_id")

        # We must translate any database field names to their corresponding
        # MongoEngine names before attempting to use them.
        translate = lambda x: model_cls._reverse_db_field_map.get(x)
        projection = [
            translate(field)
            for field in projection
            if field in model_cls._reverse_db_field_map
        ]

        if 0 in projection_value:
            qry = qry.exclude(*projection)
        else:
            # id has to be always there
            projection.append("id")
            qry = qry.only(*projection)
        return qry

    def find(self, resource, req, sub_resource_lookup):
        """
        Search for results and return list of them.

        :param resource: name of requested resource as string.
        :param req: instance of :class:`eve.utils.ParsedRequest`.
        :param sub_resource_lookup: sub-resource lookup from the endpoint url.
        """
        qry = self.cls_map.objects(resource)

        client_projection = {}
        client_sort = {}
        spec = {}

        # TODO sort syntax should probably be coherent with 'where': either
        # mongo-like # or python-like. Currently accepts only mongo-like sort
        # syntax.

        # TODO should validate on unknown sort fields (mongo driver doesn't
        # return an error)
        if req and req.sort:
            try:
                client_sort = ast.literal_eval(req.sort)
            except Exception as e:
                abort(400, description=debug_error_message(str(e)))

        if req and req.where:
            try:
                spec = self._sanitize(json.loads(req.where))
            except HTTPException as e:
                # _sanitize() is raising an HTTP exception; let it fire.
                raise
            except:
                try:
                    spec = parse(req.where)
                except ParseError:
                    abort(
                        400,
                        description=debug_error_message(
                            "Unable to parse `where` clause"
                        ),
                    )

        if sub_resource_lookup:
            spec.update(sub_resource_lookup)

        spec = self._mongotize(spec, resource)

        bad_filter = validate_filters(spec, resource)
        if bad_filter:
            abort(400, bad_filter)

        client_projection = self._client_projection(req)

        datasource, spec, projection, sort = self._datasource_ex(
            resource, spec, client_projection, client_sort
        )
        # apply ordering
        if sort:
            for field, direction in _itemize(sort):
                if direction < 0:
                    field = "-%s" % field
                qry = qry.order_by(field)
        # apply filters
        if req and req.if_modified_since:
            spec[config.LAST_UPDATED] = {"$gt": req.if_modified_since}
        if len(spec) > 0:
            qry = qry.filter(__raw__=spec)
        # apply projection
        qry = self._projection(resource, projection, qry)
        # apply limits
        if req and req.max_results:
            qry = qry.limit(int(req.max_results))
        if req and req.page > 1:
            qry = qry.skip((req.page - 1) * req.max_results)
        return PymongoQuerySet(qry)

    def find_one(
        self, resource, req, check_auth_value=True, force_auth_field_projection=False, **lookup
    ):
        """
        Look for one object.
        """
        # transform every field value to correct type for querying
        lookup = self._mongotize(lookup, resource)

        client_projection = self._client_projection(req)
        datasource, filter_, projection, _ = self._datasource_ex(
            resource, lookup, client_projection, 
            check_auth_value=check_auth_value,
            force_auth_field_projection=force_auth_field_projection
        )
        qry = self.cls_map.objects(resource)

        if len(filter_) > 0:
            qry = qry.filter(__raw__=filter_)

        qry = self._projection(resource, projection, qry)
        try:
            doc = qry.get()
            extra = dispatch_meta_properties(doc)
            check_permissions(doc, 'GET')
            doc = dict(doc.to_mongo())
            doc[app.config.get('EVE_MONGOENGINE_EXTRA_FIELD', '_extra')] = extra
            return clean_doc(doc)
        except DoesNotExist:
            return None

    def _doc_to_model(self, resource, doc):

        # Strip underscores from special key names
        if "_id" in doc:
            doc["id"] = doc.pop("_id")

        cls = self.cls_map[resource]

        # We must translate any database field names to their corresponding
        # MongoEngine names before attempting to use them.
        translate = lambda x: cls._reverse_db_field_map.get(x, x)
        doc = {translate(k): doc[k] for k in doc}

        # MongoEngine 0.9 now throws a FieldDoesNotExist when initializing a
        # Document with unknown keys.
        if MONGOENGINE_VERSION >= LooseVersion("0.9.0"):
            from mongoengine import FieldDoesNotExist

            doc_keys = set(cls._fields) & set(doc)
            try:
                instance = cls(**{k: doc[k] for k in doc_keys})
            except FieldDoesNotExist as e:
                abort(
                    422,
                    description=debug_error_message(
                        "mongoengine.FieldDoesNotExist: %s" % e
                    ),
                )
        else:
            instance = cls(**doc)

        for attr, field in iteritems(cls._fields):
            # Inject GridFSProxy object into the instance for every FileField.
            # This is because the Eve's GridFS layer does not work with the
            # model object, but handles insertion in his own workspace. Sadly,
            # there's no way how to work around this, so we need to do this
            # special hack..
            if isinstance(field, FileField):
                if attr in doc:
                    proxy = field.get_proxy_obj(key=field.name, instance=instance)
                    proxy.grid_id = doc[attr]
                    instance._data[attr] = proxy
        return instance

    def insert(self, resource, doc_or_docs):
        """Called when performing POST request"""
        datasource, filter_, _, _ = self._datasource_ex(resource)
        try:
            if not isinstance(doc_or_docs, list):
                doc_or_docs = [doc_or_docs]

            ids = []
            for doc in doc_or_docs:    
                # strip those fields calculated in _fix_fields
                remove_eve_mongoengine_fields(doc)            
                model = self._doc_to_model(resource, doc)
                check_permissions(model, 'POST')
                model.save(write_concern=self._wc(resource))
                ids.append(model.id)
                doc.update(dict(model.to_mongo()))
                doc[config.ID_FIELD] = model.id
            return ids
        except pymongo.errors.OperationFailure as e:
            # most likely a 'w' (write_concern) setting which needs an
            # existing ReplicaSet which doesn't exist. Please note that the
            # update will actually succeed (a new ETag will be needed).
            abort(
                500,
                description=debug_error_message(
                    "pymongo.errors.OperationFailure: %s" % e
                ),
            )
        except Exception as exc:
            self._handle_exception(exc)

    def update(self, resource, id_, updates, *args, **kwargs):
        """Called when performing PATCH request."""
        try:
            return self.updater.update(resource, id_, updates)
        except pymongo.errors.OperationFailure as e:
            # see comment in :func:`insert()`.
            abort(
                500,
                description=debug_error_message(
                    "pymongo.errors.OperationFailure: %s" % e
                ),
            )
        except Exception as exc:
            self._handle_exception(exc)

    def replace(self, resource, id_, document, *args, **kwargs):
        """Called when performing PUT request."""
        try:
            # FIXME: filters?
            model = self._doc_to_model(resource, document)
            check_permissions(model, 'PUT')
            model.save(write_concern=self._wc(resource))
        except pymongo.errors.OperationFailure as e:
            # see comment in :func:`insert()`.
            abort(
                500,
                description=debug_error_message(
                    "pymongo.errors.OperationFailure: %s" % e
                ),
            )
        except Exception as exc:
            self._handle_exception(exc)

    # FIXME: DELETE can be called document- or collection-wise, in the second case
    #        it is meant to drop the whole collection. Currently a document-level
    #        permission checking is performed but possibly a different check should
    #        be made for collection-wise deletion (e.g., role-based on the resource)
    #        the `for doc in qry:` loop should be changed in this latter case
    def remove(self, resource, lookup):
        """Called when performing DELETE request."""
        lookup = self._mongotize(lookup, resource)
        datasource, filter_, _, _ = self._datasource_ex(resource, lookup)

        try:
            if not filter_:
                qry = self.cls_map.objects(resource)
            else:
                qry = self.cls_map.objects(resource)(__raw__=filter_)
            # Permission checking is mandatory
            for doc in qry:
                check_permissions(doc, 'DELETE')
            qry.delete(write_concern=self._wc(resource))
        except pymongo.errors.OperationFailure as e:
            # see comment in :func:`insert()`.
            abort(
                500,
                description=debug_error_message(
                    "pymongo.errors.OperationFailure: %s" % e
                ),
            )
        except Exception as exc:
            self._handle_exception(exc)
