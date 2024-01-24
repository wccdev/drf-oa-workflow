try:
    from celery import shared_task  # noqa
except ModuleNotFoundError:
    shared_task = lambda name: type(name)  # noqa

from .utils import FetchOaDbHandler, get_sync_oa_user_model


@shared_task(name="drf_oa_workflow:同步Oa用户")
def sync_oa_users():
    """
    同步Oa用户
    """
    oa_user_model = get_sync_oa_user_model()
    all_oa_users = FetchOaDbHandler.get_all_oa_users()
    objs = []
    for i in all_oa_users:
        objs.append(oa_user_model.as_obj(i))
    oa_user_model.objects.bulk_create(
        objs,
        update_conflicts=True,
        update_fields=["staff_code_id", "dept_id", "name", "dept_name"],
        unique_fields=["user_id"],
    )
