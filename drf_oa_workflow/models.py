from django.contrib.auth import get_user_model
from django.db import models

from .settings import api_settings

UserModel = get_user_model()


class AbstractOaUserInfo(models.Model):
    user_id = models.IntegerField(unique=True, primary_key=True, verbose_name="OA用户数据ID")
    name = models.CharField(max_length=480, blank=True, default="", verbose_name="名称")
    staff_code = models.OneToOneField(
        UserModel,
        on_delete=models.DO_NOTHING,
        to_field=UserModel.USERNAME_FIELD,
        # related_name="oa_user",
        null=True,
        db_column="staff_code",
        db_constraint=False,
        verbose_name="OA用户工号",
    )
    dept_id = models.IntegerField(null=True, verbose_name="OA用户部门ID")
    dept_name = models.CharField(max_length=480, blank=True, default="", verbose_name="OA用户部门")

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

    @classmethod
    def as_obj(cls, data: dict):
        return cls(
            user_id=data[api_settings.OA_DB_USER_ID_COLUMN],
            staff_code_id=data[api_settings.OA_DB_USER_STAFF_CODE_COLUMN],
            dept_id=data[api_settings.OA_DB_USER_DEPT_ID_COLUMN],
            name=data[api_settings.OA_DB_USER_NAME_COLUMN] or "",
            dept_name=data[api_settings.OA_DB_DEPT_NAME_COLUMN] or "",
        )
