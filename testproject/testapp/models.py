from django.contrib.contenttypes.models import ContentType
from django.db import models


class Tag(models.Model):
    title = models.CharField(max_length=255)


class Project(models.Model):
    name = models.CharField(max_length=10, unique=True)
    tags = models.ManyToManyField(Tag, blank=True)


class Task(models.Model):
    project = models.ForeignKey(Project, models.PROTECT)
    name = models.CharField(max_length=10, unique=True)

