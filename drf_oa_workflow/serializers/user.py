from rest_framework import serializers

from drf_oa_workflow.utils import get_sync_oa_user_model

OAUserModel = get_sync_oa_user_model()


class WorkFlowUserSerializer(serializers.ModelSerializer):
    oa_user_id = serializers.IntegerField(source="user_id", label="OA用户ID")
    oa_user_name = serializers.CharField(source="name", label="OA用户ID")
    oa_user_dept_id = serializers.IntegerField(source="dept_id", label="OA用户部门ID")
    oa_user_dept_name = serializers.CharField(source="dept_name", label="OA用户部门")
    sys_user_id = serializers.IntegerField(source="staff_code.id", label="用户ID")
    sys_user_name = serializers.CharField(source="staff_code.name", label="用户名称")
    sys_user_code = serializers.CharField(
        source="staff_code.username", label="用户工号"
    )
    # TODO 系统用户所属部门
    sys_user_dept = serializers.CharField(read_only=True, default="", label="用户部门")
    dingtalk_avatar = serializers.CharField(
        source="staff_code.dingtalk_avatar", label="钉钉头像"
    )

    @classmethod
    def process_queryset(cls, request, queryset):
        return queryset.select_related("staff_code")

    class Meta:
        model = OAUserModel
        fields = (
            "oa_user_id",
            "oa_user_name",
            "oa_user_dept_id",
            "oa_user_dept_name",
            "sys_user_id",
            "sys_user_name",
            "sys_user_code",
            "sys_user_dept",
            "dingtalk_avatar",
        )
