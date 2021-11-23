from typing import Any

from django.conf import settings
from django.db import models, router as db_router
from django.db.models import Subquery
from django.test import TestCase

from database_routing import (ForceMasterRead,
                              force_master_read,
                              force_master_read_method,
                              MasterSlaveRouter)
from testapp.models import Project, Tag, Task


class DBRoutingTestCase(TestCase):
    """ Database router test. """

    multi_db = True
    databases = {'default', 'slave', 'tag_primary', 'tag_replica'}

    def setUp(self) -> None:
        self.router = MasterSlaveRouter()

    def test_default_primary_write(self):
        """ Default primary write test. """
        project = Project.objects.create(name='test', id=1)

        primary_qs = Project.objects.using('default').all()
        replica_qs = Project.objects.using('slave').all()

        self.assertEqual(primary_qs.count(), 1)
        self.assertEqual(primary_qs.first(), project)
        self.assertEqual(replica_qs.count(), 0)

    def test_default_replica_read(self):
        """ Default replica read test. """
        project = Project.objects.using('slave').create(name='test', id=1)

        primary_qs = Project.objects.using('default').all()
        replica_qs = Project.objects.all()  # read from replica

        self.assertEqual(primary_qs.count(), 0)
        self.assertEqual(replica_qs.count(), 1)
        self.assertEqual(replica_qs.first(), project)

    def test_primary_write__if_defined_for_model(self):
        """ Primary write test, overridden for model. """
        tag = Tag.objects.create(title='test', id=1)

        primary_qs = Tag.objects.using('tag_primary').all()
        replica_qs = Tag.objects.using('tag_replica').all()

        self.assertEqual(primary_qs.count(), 1)
        self.assertEqual(primary_qs.first(), tag)
        self.assertEqual(replica_qs.count(), 0)

    def test_replica_read__if_defined_for_model(self):
        """ Replica read test, overridden for model."""
        tag = Tag.objects.using('tag_replica').create(title='test', id=1)

        primary_qs = Tag.objects.using('tag_primary').all()
        replica_qs = Tag.objects.all()  # read from Tag_replica

        self.assertEqual(primary_qs.count(), 0)
        self.assertEqual(replica_qs.count(), 1)
        self.assertEqual(replica_qs.first(), tag)

    def test_context_manager_force_primary_read(self):
        """ Context manager test for reading from the primary. """
        project = Project.objects.using('default').create(name='test', id=1)

        with ForceMasterRead():
            primary_count = Project.objects.all().count()
            primary_project = Project.objects.get(id=project.id)

        self.assertEqual(primary_count, 1)
        self.assertEqual(primary_project, project)

    def test_decorator_force_primary_read(self):
        """ Decorator test for reading from primary. """
        project = Project.objects.using('default').create(name='test', id=1)

        @force_master_read
        def read_from_primary(project_id: int) -> (int, Any):
            count = Project.objects.all().count()
            obj = Project.objects.get(id=project_id)
            return count, obj

        primary_count, primary_project = read_from_primary(project.id)

        self.assertEqual(primary_count, 1)
        self.assertEqual(primary_project, project)

    def test_class_decorator_force_primary_read(self):
        """ Class decorator test for reading from primary. """
        project = Project.objects.using('default').create(name='test', id=1)

        @force_master_read_method(methods=['read'])
        class PrimaryReader:
            def read(self, project_id: int) -> (int, Any):
                count = Project.objects.all().count()
                obj = Project.objects.get(id=project_id)
                return count, obj

        primary_count, primary_project = PrimaryReader().read(project.id)

        self.assertEqual(primary_count, 1)
        self.assertEqual(primary_project, project)

    def test_allowed_relation__if_from_one_db(self):
        """ Test relations, if objects are from one DB. """
        project = Project.objects.create(name='test', id=1)

        Task.objects.create(name='default', project=project)  # w/o exception

    def test_denied_relation__if_from_different_db(self):
        """ Error relation test if objects are from different DB. """
        project = Project.objects.create(name='primary db', id=1)
        tag = Tag.objects.create(title='tag db')

        with self.assertRaises(ValueError):
            project.tags.add(tag)

    def test_get_default_db_config(self):
        """ Test of DB configuration retrieval. """
        default_config = self.router.get_db_config(Project)
        custom_config = self.router.get_db_config(Tag)

        expected = settings.MASTER_SLAVE_ROUTING['testapp.tag']

        self.assertEqual(default_config, {})
        self.assertEqual(custom_config, expected)

    def test_get_db_for_read(self):
        """ Test of getting the DB for reading. """
        default_db = self.router.db_for_read(Project)
        custom_db = self.router.db_for_read(Tag)

        expected = settings.MASTER_SLAVE_ROUTING['testapp.tag']['read']

        self.assertEqual(default_db, 'slave')
        self.assertEqual(custom_db, expected)

    def test_get_db_for_write(self):
        """ Test of getting a DB for writing. """
        default_db = self.router.db_for_write(Project)
        custom_db = self.router.db_for_write(Tag)

        expected = settings.MASTER_SLAVE_ROUTING['testapp.tag']['write']

        self.assertEqual(default_db, 'default')
        self.assertEqual(custom_db, expected)

    def test_allow_syncdb(self):
        """ Test of schema creation."""
        write_db = self.router.allow_syncdb('default', Project)
        read_db = self.router.allow_syncdb('slave', Project)
        custom_write_db = self.router.allow_syncdb('tag_primary', Tag)
        custom_read_db = self.router.allow_syncdb('tag_replica', Tag)

        self.assertTrue(write_db)
        self.assertFalse(read_db)
        self.assertTrue(custom_write_db)
        self.assertFalse(custom_read_db)

    def test_allow_relation(self):
        """ Relations are allowed only from one DB. """
        allow_relation = db_router.allow_relation(Project, Task)
        deny_relation = db_router.allow_relation(Project, Tag)

        self.assertTrue(allow_relation)
        self.assertFalse(deny_relation)

    def test_filter_for_diff_db(self):
        """ Filter by related field from different DB. """
        project = Project.objects.create(name='primary db', id=1)
        Task.objects.create(name='default', project=project)

        with ForceMasterRead():
            tasks = Task.objects.filter(project__tags__isnull=True)
            tags = tasks.first().project.tags.all()

            self.assertEqual(len(tags), 0)

    def test_values_for_diff_db(self):
        """ Getting the values of a related field from different DB. """
        project = Project.objects.create(name='primary db', id=1)
        Task.objects.create(name='default', project=project)

        with ForceMasterRead():
            values = Project.objects.values('tags__title')

            self.assertEqual(values[0]['tags__title'], None)

    def test_subquery_for_diff_db(self):
        """ Test subquery from different DB. """
        tag = Tag.objects.create(title='my tag')
        project = Project.objects.create(name='primary db', id=1)
        task = Task.objects.create(name='my task', project=project)

        tags = Tag.objects.using('tag_primary').filter(
            pk=tag.pk
        ).values('title')
        tasks = Task.objects.using('default').filter(
            pk=task.pk
        ).values('name')

        with ForceMasterRead():
            project = Project.objects.annotate(
                tag_title=Subquery(tags, output_field=models.CharField()),
                task_name=Subquery(tasks, output_field=models.CharField())
            ).first()

        self.assertEqual(tags[0]['title'], 'my tag')
        self.assertEqual(project.task_name, 'my task')
        self.assertEqual(project.tag_title, None)  # since different DB

    def test_allow_migrate(self):
        """ Migrate are allowed for all DB. """
        self.assertTrue(db_router.allow_migrate('default', 'testapp'))
        self.assertTrue(db_router.allow_migrate('slave', 'testapp'))
        self.assertTrue(db_router.allow_migrate('tag_primary', 'testapp'))
        self.assertTrue(db_router.allow_migrate('tag_replica', 'testapp'))

    def test_allow_migrate_model(self):
        """ Migrate model are allowed for all DB. """
        self.assertTrue(db_router.allow_migrate_model('default', Project))
        self.assertTrue(db_router.allow_migrate_model('default', Tag))

        self.assertTrue(db_router.allow_migrate_model('slave', Project))
        self.assertTrue(db_router.allow_migrate_model('slave', Tag))

        self.assertTrue(db_router.allow_migrate_model('tag_primary', Project))
        self.assertTrue(db_router.allow_migrate_model('tag_primary', Tag))

        self.assertTrue(db_router.allow_migrate_model('tag_replica', Project))
        self.assertTrue(db_router.allow_migrate_model('tag_replica', Tag))
