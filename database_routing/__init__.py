# coding: utf-8
import functools

from django.db import connections
from django.conf import settings


class MasterSlaveRouter(object):
    """Django database router for Master/Slave replication scheme support.

    Example configuration:

    MASTER_SLAVE_ROUTING = {
        'my_app.MySQLModel': {
            'read': 'mysql_slave',
            'write': 'mysql_default'
        },
        'postgre_app': {
            'read': 'psql_slave',
            'write': 'psql_master
    }

    DATABASE_ROUTERS = ['database_routing.MasterSlaveRouter']

    If model is not present in MASTER_SLAVE_ROUTING setting, returns
    'default' connection for write and 'slave' connection for read
    """
    _lookup_cache = {}

    default_read = 'slave'
    default_write = 'default'

    def get_db_config(self, model):
        """ Returns the database configuration for `model`."""
        app_label = model._meta.app_label
        model_name = model._meta.model_name
        model_label = '%s.%s' % (app_label, model_name)

        if model_label not in self._lookup_cache:
            conf = getattr(settings, 'MASTER_SLAVE_ROUTING', {})

            if model_label in conf:
                result = conf[model_label]
            elif app_label in conf:
                result = conf[app_label]
            else:
                result = {}
            self._lookup_cache[model_label] = result
        return self._lookup_cache[model_label]

    def db_for_read(self, model, **hints):
        db_config = self.get_db_config(model)
        return db_config.get('read', self.default_read)

    def db_for_write(self, model, **hints):
        db_config = self.get_db_config(model)
        return db_config.get('write', self.default_write)

    def allow_syncdb(self, db, model):
        """ Schema creation allowed only for write DB."""
        syncdb = self.db_for_write(model)
        return db == syncdb

    def allow_relation(self, obj1, obj2, **hints):
        """ Relations are allowed only from one database."""
        db_for_write_1 = self.db_for_write(obj1)
        db_for_write_2 = self.db_for_write(obj2)
        return db_for_write_1 == db_for_write_2


class ForceMasterRead(object):
    """ Context manager that switches all reads to Master database.

    """

    def __enter__(self):
        """ Sets Master as db_for_read

        :return: write-enabled connection
        """
        self._prev_read = MasterSlaveRouter.default_read
        MasterSlaveRouter.default_read = MasterSlaveRouter.default_write
        return connections[MasterSlaveRouter.default_read]

    def __exit__(self, exc_type, exc_val, exc_tb):
        """ Resets db_for_read to it's previous value."""
        MasterSlaveRouter.default_read = self._prev_read


def force_master_read(func):
    """ Decorates a func with ForceMasterRead context.

    :param func: any callable that needs to do reads from Master DB
    :returns: decorated function

    Example:

    @force_master_read
    def do_some_update():
        # reading obj from Master database
        obj = MyModel.objects.first()
        obj.field = 'value'
        obj.save()
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with ForceMasterRead():
            return func(*args, **kwargs)

    return wrapper


def force_master_read_method(methods=()):
    """ Decorates some methods of class with ForceMasterRead context.

     :param methods: list-like, names of methods need to be decorated
    :returns decorated class

    Example:

    @force_master_read_methods(methods=['do_some_update'])
    class MyModelUpdater(object):

        def do_some_update(self):
            # reading obj from Master database
            obj = MyModel.objects.first()
            obj.field = 'value'
            obj.save()

        def do_other_update(self):
            # reading obj from Slave database
            obj = MyModel.objects.last()
            obj.field = 'dirty'
            obj.save()

    """

    def decorator(cls):
        for m in methods:
            # decorate methods with force_master_read decorator
            if hasattr(cls, m):
                setattr(cls, m, force_master_read(getattr(cls, m)))
        return cls

    return decorator
