try:
    from celery import shared_task
except ModuleNotFoundError:
    shared_task = lambda name: type(name)  # noqa: E731

from drf_oa_workflow.models import HRMResource
from drf_oa_workflow.models import OaUserInfo


@shared_task(name="drf_oa_workflow:同步OA用户")
def sync_oa_users():
    """
    同步Oa用户
    """
    all_oa_users = HRMResource.objects.select_related("DEPARTMENTID").all()
    objs = [
        OaUserInfo(
            user_id=i.ID,
            name=i.LASTNAME,
            staff_code_id=i.LOGINID,
            dept_id=i.DEPARTMENTID_id,
            dept_name=i.DEPARTMENTID.DEPARTMENTNAME if i.DEPARTMENTID else "",
        )
        for i in all_oa_users
    ]
    OaUserInfo.objects.bulk_create(
        objs,
        update_conflicts=True,
        update_fields=["staff_code_id", "dept_id", "name", "dept_name"],
        unique_fields=["user_id"],
    )
