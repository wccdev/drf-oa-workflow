try:
    from celery import shared_task
except ModuleNotFoundError:
    shared_task = lambda name: type(name)  # noqa: E731

from drf_oa_workflow.models import HRMResource
from drf_oa_workflow.models import OaUserInfo
from drf_oa_workflow.utils import get_sync_oa_user_model


@shared_task(name="drf_oa_workflow:同步OA用户")
def sync_oa_users():
    """
    同步Oa用户
    """
    if get_sync_oa_user_model() != OaUserInfo:
        return (
            "此方法仅在使用默认OA用户信息模型drf_oa_workflow.models.OaUserInfo有效，"
            "\n系统已重新定义OA用户信息模型，为防止任务执行错误，请重新定义同步任务。"
        )

    all_oa_users = HRMResource.objects.select_related("DEPARTMENTID").all()
    objs = [
        OaUserInfo(
            user_id=i.ID,
            name=i.LASTNAME,
            staff_code_id=i.LOGINID,
            dept_id=i.DEPARTMENTID_id,
            dept_name=i.DEPARTMENTID.DEPARTMENTNAME if i.DEPARTMENTID else "",
            status=i.STATUS,
        )
        for i in all_oa_users
    ]
    OaUserInfo.objects.bulk_create(
        objs,
        update_conflicts=True,
        update_fields=["staff_code_id", "dept_id", "name", "dept_name", "status"],
        unique_fields=["user_id"],
    )
    return None
