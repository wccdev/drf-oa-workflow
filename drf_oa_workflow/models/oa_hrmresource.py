from django.db import models

from drf_oa_workflow.db.models import OADbBaseModel

__all__ = ["HRMDepartment", "HRMResource"]


class HRMDepartment(OADbBaseModel):
    """
    OA部门
    """

    ID = models.IntegerField(primary_key=True)
    DEPARTMENTNAME = models.CharField(max_length=200, verbose_name="部门名称")

    def __str__(self):
        return self.DEPARTMENTNAME

    class Meta:
        managed = False
        db_table = 'ECOLOGY"."HRMDEPARTMENT'
        verbose_name = verbose_name_plural = "OA部门"


class HRMResource(OADbBaseModel):
    """
    OA人员
    """

    ID = models.IntegerField(primary_key=True)
    LOGINID = models.CharField(max_length=300, unique=True, verbose_name="登入名")
    LASTNAME = models.CharField(max_length=200, verbose_name="姓名")
    DEPARTMENTID = models.ForeignKey(
        HRMDepartment,
        db_column="DEPARTMENTID",
        to_field="ID",
        null=True,
        on_delete=models.DO_NOTHING,
        verbose_name="部门ID",
    )
    STATUS = models.IntegerField(null=True, verbose_name="状态")

    def __str__(self):
        return self.LASTNAME

    class Meta:
        managed = False
        db_table = 'ECOLOGY"."HRMRESOURCE'
        verbose_name = verbose_name_plural = "OA人员"
