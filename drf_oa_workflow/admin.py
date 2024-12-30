from django.contrib import admin

# from django.contrib.auth import get_user_model
from django.db.models import Case
from django.db.models import F
from django.db.models import Value
from django.db.models import When

from .models import OaUserInfo


@admin.register(OaUserInfo)
class OaUserInfoAdmin(admin.ModelAdmin):
    exclude = ("staff_code",)
    list_display = (
        "user_id",
        "name",
        "staff_code_str",
        "dept_id",
        "dept_name",
        "status",
        "has_system_user",
        "system_user",
    )
    readonly_fields = ("user_id", "name", "staff_code_str", "dept_id", "dept_name")
    search_fields = ["user_id", "name", "staff_code_str", "dept_name"]
    search_help_text = "查询OA用户ID、名称、工号或者部门"
    list_per_page = 20

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("staff_code")
            .annotate(staff_code_str=F("staff_code_id"))
            .annotate(
                has_system_user=Case(
                    When(staff_code__id__isnull=False, then=Value(True)),  # noqa: FBT003
                    default=Value(False),  # noqa: FBT003
                )
            )
            .order_by("-has_system_user")
        )

    @admin.display(description="OA用户工号")
    def staff_code_str(self, obj):
        return obj.staff_code_str

    @admin.display(description="有相关系统用户", boolean=True)
    def has_system_user(self, obj):
        return obj.has_system_user

    @admin.display(description="相关本系统用户")
    def system_user(self, obj):
        if obj.staff_code:
            return (
                f"{obj.staff_code.id}-{obj.staff_code.username}-{obj.staff_code.name}"
            )
        return obj.staff_code

    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions

    def delete_model(self, request, obj):
        # self.message_user(request, "此数据无法删除", level=messages.ERROR)
        return

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
