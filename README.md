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
  PRIMARY_REPLICA_ROUTING = {
    'my_app.MyModel': {
      'read': 'custom_connection',
      'write': 'custom_connection
    }
  }
  
  ```
  
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
  
