django-database-routing
===================

Provides Master/Slave database router for Django.
See https://docs.djangoproject.com/en/dev/topics/db/multi-db/#an-example for example implementation.

Configuration
-------------
1. Add router to settings.py
  ```python
  DATABASE_ROUTERS = ['database_routing.MasterSlaveRouter']
  
  ```
2. Configure 'default' and 'slave' connections in `settings.DATABASES`
3. If needed you can force specific connections for some apps or models:
  ```python
  MASTER_SLAVE_ROUTING = {
    'my_app.MyModel': {
      'read': 'custom_connection',
      'write': 'custom_connection
    }
  }
  
  ```
  
Forcing reading from master
---------------------------

When transaction isolation level or replication lag causing bugs in your project, you can force your code 
to read all the data from `default` (or master) database.

```python
from database_routing import force_master_read
@force_master_read
def do_some_reads_and_updates():
    # All Django ORM queries are going to 'default' database here.
    # ...
    
```
  
