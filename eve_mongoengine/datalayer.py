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
import traceback
import pymongo
from distutils.version import LooseVersion
from uuid import UUID
from flask import abort
from eve.exceptions import ConfigException
from eve.io.mongo import MongoJSONEncoder, Mongo
from eve.utils import config, debug_error_message, validate_filters
from mongoengine import (
    __version__,
    DoesNotExist,
    FileField,
    BulkWriteError,
    NotUniqueError,
)
from mongoengine.connection import get_db, connect

# --- Third Party ---
from pymongo.errors import DuplicateKeyError

# Python3 compatibility
from ._compat import iteritems

MONGOENGINE_VERSION = LooseVersion(__version__)


def _itemize(maybe_dict):
    if isinstance(maybe_dict, list):
        return maybe_dict
    elif isinstance(maybe_dict, dict):
        return iteritems(maybe_dict)
    else:
        raise TypeError("Wrong type to itemize. Allowed lists and dicts.")


def clean_doc(doc):
    """
    clean helper fields
    # https://stackoverflow.com/questions/13824569/mongoengine-types-and-cls-fields
    """

    doc.pop("_cls", None)
    return doc


class PymongoQuerySet(object):
    """
    Dummy mongoenigne-like QuerySet behaving just like queryset
    with as_pymongo() called, but returning ALL fields in subdocuments
    (which as_pymongo() somehow filters).
    """

    def __init__(self, qs):
        self._qs = qs

    def __iter__(self):
        def iterate(obj):
            qs = object.__getattribute__(obj, "_qs")
            for doc in qs:
                # MPI-1220#2
                # doc = dict(doc.to_mongo())
                # for attr, value in iteritems(dict(doc)):
                #     if isinstance(value, (list, dict)) and not value:
                #         del doc[attr]
                doc = doc.to_mongo()
                doc = clean_doc(doc)
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
        Returns QuerySet instance of resource's class thourh mongoengine
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
    dirty and there would be unnecessary 'helper' methods in the main class
    MongoengineDataLayer causing namespace pollution.
    """

    def __init__(self, datalayer):
        self.datalayer = datalayer

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

    def _update_using_update_one(self, resource, id_, updates):
        """
        Updates one document atomically using QuerySet.update_one().
        """
        kwargs = self._transform_updates_to_mongoengine_kwargs(resource, updates)
        qset = lambda: self.datalayer.cls_map.objects(resource)
        qry = qset()(id=id_)
        res = qry.update_one(write_concern=self.datalayer._wc(resource), **kwargs)
        return res

    def _update_document(self, doc, updates):
        """
        Makes appropriate calls to update mongoengine document properly by
        update definition given from REST API.
        """
        for db_field, value in iteritems(updates):
            field_name = doc._reverse_db_field_map[db_field]
            field = doc._fields[field_name]
            if value is None:
                doc[field_name] = value
            else:
                doc[field_name] = field.to_python(value)
        return doc

    def _update_using_save(self, resource, id_, updates):
        """
        Updates one document non-atomically using Document.save().
        """
        model = self.datalayer.cls_map.objects(resource)(id=id_).get()
        self._update_document(model, updates)
        model.save(write_concern=self.datalayer._wc(resource))
        return model

    def update(self, resource, id_, updates):
        """
        Resolves update for PATCH request.

        Does not handle mongo errros!
        """
        opt = self.datalayer.mongoengine_options

        if opt.get("use_document_save_for_patch", True):
            res = self._update_using_save(resource, id_, updates)
        else:
            res = self._update_using_update_one(resource, id_, updates)

        return res


class MongoengineDataLayer(Mongo):
    """
    Data layer for eve-mongoengine extension.

    Most of functionality is copied from :class:`eve.io.mongo.Mongo`.
    """

    #: default JSON encoder
    json_encoder_class = MongoengineJsonEncoder

    #: name of default queryset, where datalayer asks for data
    default_queryset = "objects"

    #: Options for usage of mongoengine layer.
    #: use_document_save_for_patch - when set to True, Mongoengine layer will
    #: use update_one() method (which is atomic) for updating. But then you
    #: will loose your pre/post-save hooks. When you set this to False, for
    #: updating will be used save() method.
    mongoengine_options = {
        "use_document_save_for_patch": False,
        "use_document_save_for_insert": False,
        "use_document_delete_for_delete": False,
    }

    def __init__(self, ext):
        """
        Constructor.

        :param ext: instance of :class:`EveMongoengine`.
        """
        # get authentication info
        username = ext.app.config.get("MONGO_USERNAME", None)
        password = ext.app.config.get("MONGO_PASSWORD", None)
        auth_source = ext.app.config.get("MONGO_AUTH_SOURCE", None)
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
            self.driver.db.authenticate(username, password, source=auth_source)
        # helper object for managing PATCHes, which are a bit dirty
        self.updater = MongoengineUpdater(self)
        # map resource -> Mongoengine class
        self.cls_map = ResourceClassMap(self)

    def _handle_exception(self, exc):
        """
        If application is in debug mode, prints every traceback to stderr.
        """
        self.app.logger.exception(exc)
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

        projection_copy = projection.copy()
        projection = []
        for field in projection_copy:
            field_copy = field.split(".")
            field_copy[0] = translate(field_copy[0])
            if None not in field_copy:
                projection.append(".".join(field_copy))

        if 0 in projection_value:
            qry = qry.exclude(*projection)
        else:
            # id has to be always there
            projection.append("id")
            qry = qry.only(*projection)
        return qry

    def find(self, resource, req, sub_resource_lookup, perform_count=True):
        """
        Seach for results and return list of them.

        :param resource: name of requested resource as string.
        :param req: instance of :class:`eve.utils.ParsedRequest`.
        :param sub_resource_lookup: sub-resource lookup from the endpoint url.
        """
        args = dict()

        if req and req.max_results:
            args["limit"] = req.max_results

        if req and req.page > 1:
            args["skip"] = (req.page - 1) * req.max_results

        # TODO sort syntax should probably be coherent with 'where': either
        # mongo-like # or python-like. Currently accepts only mongo-like sort
        # syntax.

        # TODO should validate on unknown sort fields (mongo driver doesn't
        # return an error)

        client_sort = self._convert_sort_request_to_dict(req)
        spec = self._convert_where_request_to_dict(resource, req)

        bad_filter = validate_filters(spec, resource)
        if bad_filter:
            abort(400, bad_filter)

        if sub_resource_lookup:
            spec = self.combine_queries(spec, sub_resource_lookup)

        if (
            config.DOMAIN[resource]["soft_delete"]
            and not (req and req.show_deleted)
            and not self.query_contains_field(spec, config.DELETED)
        ):
            # Soft delete filtering applied after validate_filters call as
            # querying against the DELETED field must always be allowed when
            # soft_delete is enabled
            spec = self.combine_queries(spec, {config.DELETED: {"$ne": True}})

        spec = self._mongotize(spec, resource)

        client_projection = self._client_projection(req)

        datasource, spec, projection, sort = self._datasource_ex(
            resource, spec, client_projection, client_sort
        )

        if len(spec) > 0:
            args["filter"] = spec

        if sort is not None:
            args["sort"] = sort

        if projection:
            args["projection"] = projection

        qry = self.cls_map.objects(resource)

        # apply ordering
        if sort:
            sort_fields = []
            for field, direction in _itemize(sort):
                if direction < 0:
                    field = "-%s" % field
                sort_fields.append(field)
            qry = qry.order_by(*sort_fields)

        if len(spec) > 0:
            qry = qry.filter(__raw__=spec)
        # apply projection
        qry = self._projection(resource, projection, qry)
        # apply limits
        if args.get("limit"):
            qry = qry.limit(int(args["limit"]))
        if args.get("skip"):
            qry = qry.skip(args["skip"])

        count = None
        if perform_count:
            count = qry.count()
        return PymongoQuerySet(qry), count

    def find_one(
        self,
        resource,
        req,
        check_auth_value=True,
        force_auth_field_projection=False,
        **lookup
    ):
        """
        Look for one object.
        """
        # transform every field value to correct type for querying
        lookup = self._mongotize(lookup, resource)

        client_projection = self._client_projection(req)
        datasource, filter_, projection, _ = self._datasource_ex(
            resource,
            lookup,
            client_projection,
            check_auth_value=check_auth_value,
            force_auth_field_projection=force_auth_field_projection,
        )

        if (
            (config.DOMAIN[resource]["soft_delete"])
            and (not req or not req.show_deleted)
            and (not self.query_contains_field(lookup, config.DELETED))
        ):
            filter_ = self.combine_queries(filter_, {config.DELETED: {"$ne": True}})

        qry = self.cls_map.objects(resource)

        if len(filter_) > 0:
            qry = qry.filter(__raw__=filter_)

        qry = self._projection(resource, projection, qry)
        try:
            doc = dict(qry.get().to_mongo())
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

        # MongoEngine 0.9 now throws an FieldDoesNotExist when initializing a
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
        cls = self.cls_map[resource]
        try:
            if not isinstance(doc_or_docs, list):
                doc_or_docs = [doc_or_docs]

            ids = []
            models = []
            for doc in doc_or_docs:
                clean_doc(doc)
                model = self._doc_to_model(resource, doc)
                models.append(model)
            if self.mongoengine_options["use_document_save_for_insert"]:
                for model in models:
                    model.save()
                    ids.append(model.id)
            else:
                ids = cls.objects.insert(
                    models, load_bulk=False, write_concern=self._wc(resource)
                )

            return ids
        except BulkWriteError as e:
            # most likely a 'w' (write_concern) setting which needs an
            # existing ReplicaSet which doesn't exist. Please note that the
            # update will actually succeed (a new ETag will be needed).
            abort(
                400,
                description=debug_error_message(
                    "pymongo.errors.OperationFailure: %s" % e
                ),
            )
        except (DuplicateKeyError, NotUniqueError) as e:
            abort(
                400,
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

    def remove(self, resource, lookup):
        """Called when performing DELETE request."""
        lookup = self._mongotize(lookup, resource)
        datasource, filter_, _, _ = self._datasource_ex(resource, lookup)

        try:
            if not filter_:
                qry = self.cls_map.objects(resource)
            else:
                qry = self.cls_map.objects(resource)(__raw__=filter_)
            if self.mongoengine_options["use_document_delete_for_delete"]:
                for doc in qry:
                    doc.delete()
            else:
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
