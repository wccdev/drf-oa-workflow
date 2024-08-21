from django.conf import settings
from django.db import models

__all__ = [
    "AbstractOaUserInfo",
    "OaUserInfo",
]


class AbstractOaUserInfo(models.Model):
    user_id = models.IntegerField(
        unique=True, primary_key=True, verbose_name="OA用户数据ID"
    )
    name = models.CharField(max_length=480, blank=True, default="", verbose_name="名称")
    staff_code = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.DO_NOTHING,
        to_field="username",
        # related_name="oa_user",
        null=True,
        db_column="staff_code",
        db_constraint=False,
        verbose_name="OA用户工号",
    )
    dept_id = models.IntegerField(null=True, verbose_name="OA用户部门ID")
    dept_name = models.CharField(
        max_length=480, blank=True, default="", verbose_name="OA用户部门"
    )

    class Meta:
        abstract = True
        verbose_name = verbose_name_plural = "OA用户信息"


class OaUserInfo(AbstractOaUserInfo):
    """
    Users within the Django authentication system are represented by this
    model.

    Username and password are required. Other fields are optional.
    """

    class Meta(AbstractOaUserInfo.Meta):
        swappable = "SYNC_OA_USER_MODEL"

    def __str__(self):
        return self.name
