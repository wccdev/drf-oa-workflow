from django.db import models

from drf_oa_workflow.choices import StatusChoice


class BaseModel(models.Model):
    """
    标准抽象模型,可直接继承使用
    """

    status = models.SmallIntegerField(
        verbose_name="状态", choices=StatusChoice.choices, default=StatusChoice.VALID
    )
    deleted_at = models.DateTimeField("删除时间", editable=False, null=True, blank=True)
    created_at = models.DateTimeField(verbose_name="新增时间", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="更新时间", auto_now=True)

    objects = models.Manager()

    class Meta:
        abstract = True
        verbose_name = "基础模型"
