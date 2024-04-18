from django.db import models

from .manager import BaseOADbManager


class OADbBaseModel(models.Model):
    objects = BaseOADbManager()

    class Meta:
        abstract = True
