django-database-routing
===================

Provides Primary/Replica database router for Django.
See https://docs.djangoproject.com/en/dev/topics/db/multi-db/#an-example for example implementation.

![build](https://github.com/just-work/django-database-routing/workflows/build/badge.svg?branch=master)

Configuration
-------------
1. Add router to settings.py
  ```python
  DATABASE_ROUTERS = ['database_routing.PrimaryReplicaRouter']
  
  ```
2. Configure 'default' and 'replica' connections in `settings.DATABASES`
3. If needed you can force specific connections for some apps or models:
```python
DEFAULT_DB = 'default'

REPLICA_DATABASES = ['replica1', 'replica2']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': name,
        'USER': user,
        'PASSWORD': password,
        'HOST': 'host_1,host_2,host_3',
        'PORT': port,
        'OPTIONS': {
            'target_session_attrs': 'read-write',  # Connect only to the primary
        }
    },
    'replica1': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': name,
        'USER': user,
        'PASSWORD': password,
        'HOST': 'host_1,host_2,host_3',
        'PORT': port,
        'OPTIONS': {
            'target_session_attrs': 'read-only',  # Connect to any
        }
    },
    'replica2': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': name,
        'USER': user,
        'PASSWORD': password,
        'HOST': 'host_1,host_2,host_3',
        'PORT': port,
        'OPTIONS': {
            'target_session_attrs': 'read-only',  # Connect to any
        }
    },

}
```
Basic configuration option

```python
PRIMARY_REPLICA_ROUTING = {
    'all_project': {
        'read': 'replica',  # Reading is done from a replica
        'write': 'default'  # Writing is done to the primary database
    }
}
```
Configuration option with separate models for different databases
```python
PRIMARY_REPLICA_ROUTING = {
    'my_app.MySQLModel': {
        'read': 'mysql_replica',
        'write': 'mysql_default'
    },
    'postgres_app': {
        'read': 'psql_replica',
        'write': 'psql_primary'
    }
}

```
If the model is not present in the PRIMARY_REPLICA_ROUTING settings,
it returns the 'default' connection for write operations or a random replica for read operations.
  
Forcing reading from primary
---------------------------

When transaction isolation level or replication lag causing bugs in your project, you can force your code 
to read all the data from `default` (or primary) database.

```python
from database_routing import force_primary_read
@force_primary_read
def do_some_reads_and_updates():
    # All Django ORM queries are going to 'default' database here.
    # ...
    
```
  
