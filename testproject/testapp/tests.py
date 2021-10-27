from typing import Any

from django.test import TestCase

from database_routing import (ForceMasterRead,
                              force_master_read,
                              force_master_read_method)
from testapp.models import Project, Tag, Task


class DBRoutingTestCase(TestCase):
    """ Database router test. """

    databases = {'default', 'slave', 'tag_master', 'tag_slave'}

    def test_default_master_write(self):
        """ Default master write test. """
        project = Project.objects.create(name='test', id=1)

        master_qs = Project.objects.using('default').all()
        slave_qs = Project.objects.using('slave').all()

        self.assertEqual(master_qs.count(), 1)
        self.assertEqual(master_qs.first(), project)
        self.assertEqual(slave_qs.count(), 0)

    def test_default_slave_read(self):
        """ Default slave read test. """
        project = Project.objects.using('slave').create(name='test', id=1)

        master_qs = Project.objects.using('default').all()
        slave_qs = Project.objects.all()  # read from slave

        self.assertEqual(master_qs.count(), 0)
        self.assertEqual(slave_qs.count(), 1)
        self.assertEqual(slave_qs.first(), project)

    def test_master_write__if_defined_for_model(self):
        """ Master write test, overridden for model. """
        tag = Tag.objects.create(title='test', id=1)

        master_qs = Tag.objects.using('tag_master').all()
        slave_qs = Tag.objects.using('tag_slave').all()

        self.assertEqual(master_qs.count(), 1)
        self.assertEqual(master_qs.first(), tag)
        self.assertEqual(slave_qs.count(), 0)

    def test_slave_read__if_defined_for_model(self):
        """ Slave read test, overridden for model."""
        tag = Tag.objects.using('tag_slave').create(title='test', id=1)

        master_qs = Tag.objects.using('tag_master').all()
        slave_qs = Tag.objects.all()  # read from Tag_slave

        self.assertEqual(master_qs.count(), 0)
        self.assertEqual(slave_qs.count(), 1)
        self.assertEqual(slave_qs.first(), tag)

    def test_context_manager_force_master_read(self):
        """ Context manager test for reading from the master. """
        project = Project.objects.using('default').create(name='test', id=1)

        with ForceMasterRead():
            master_count = Project.objects.all().count()
            master_project = Project.objects.get(id=project.id)

        self.assertEqual(master_count, 1)
        self.assertEqual(master_project, project)

    def test_decorator_force_master_read(self):
        """ Decorator test for reading from master. """
        project = Project.objects.using('default').create(name='test', id=1)

        @force_master_read
        def read_from_master(project_id: int) -> (int, Any):
            count = Project.objects.all().count()
            obj = Project.objects.get(id=project_id)
            return count, obj

        master_count, master_project = read_from_master(project.id)

        self.assertEqual(master_count, 1)
        self.assertEqual(master_project, project)

    def test_class_decorator_force_master_read(self):
        """ Class decorator test for reading from master. """
        project = Project.objects.using('default').create(name='test', id=1)

        @force_master_read_method(methods=['read'])
        class MasterReader:
            def read(self, project_id: int) -> (int, Any):
                count = Project.objects.all().count()
                obj = Project.objects.get(id=project_id)
                return count, obj

        master_count, master_project = MasterReader().read(project.id)

        self.assertEqual(master_count, 1)
        self.assertEqual(master_project, project)

    def test_allowed_relation__if_from_one_db(self):
        """ Test relations, if objects are from one DB. """
        project = Project.objects.create(name='test', id=1)

        Task.objects.create(name='default', project=project)  # w/o exception

    def test_denied_relation__if_from_different_db(self):
        """ Error relation test if objects are from different DB. """
        project = Project.objects.create(name='default db', id=1)
        tag = Tag.objects.create(title='tag db')

        with self.assertRaises(ValueError):
            project.tags.add(tag)
