from django import forms
from django.contrib import admin
from django.contrib import messages
from django.db.models import Case
from django.db.models import F
from django.db.models import Value
from django.db.models import When
from django.forms import fields as form_fields
from django.http.response import HttpResponseRedirect

from .models import OaUserInfo
from .models import WorkflowBase
from .models import WorkflowType
from .models.workflow_register import OAWorkflow
from .models.workflow_register import OAWorkflowEdge
from .models.workflow_register import OAWorkflowNode
from .models.workflow_register import OAWorkflowType


@admin.register(OaUserInfo)
class OaUserInfoAdmin(admin.ModelAdmin):
    exclude = ("staff_code",)
    list_display = (
        "user_id",
        "name",
        "staff_code_str",
        "dept_id",
        "dept_name",
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


@admin.register(OAWorkflowType)
class OAWorkflowTypeAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "workflow_type_id",
        "workflow_type_name",
        "desc",
        "order",
        "uuid",
    ]
    change_list_template = "drf_oa_workflow/workflowTypeList.html"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions

    def import_data(self, request, type_id):
        if oa_workflow_type := WorkflowType.objects.filter(ID=type_id).first():
            creates = [
                OAWorkflowType(
                    workflow_type_id=oa_workflow_type.ID,
                    workflow_type_name=oa_workflow_type.TYPENAME,
                    desc=oa_workflow_type.TYPEDESC,
                    order=oa_workflow_type.DSPORDER,
                    uuid=oa_workflow_type.UUID,
                    deleted_at=None,
                )
            ]
            OAWorkflowType.objects.bulk_create(
                creates,
                update_conflicts=True,
                update_fields=[
                    "workflow_type_name",
                    "desc",
                    "order",
                    "uuid",
                    "deleted_at",
                ],
                unique_fields=["workflow_type_id"],
            )

    def upsert_data(self, request):
        exits_ids = list(
            OAWorkflowType.objects.values_list("workflow_type_id", flat=True)
        )
        oa_types = [
            OAWorkflowType(
                workflow_type_id=i.ID,
                workflow_type_name=i.TYPENAME,
                desc=i.TYPEDESC,
                order=i.DSPORDER,
                uuid=i.UUID,
            )
            for i in WorkflowType.objects.filter(ID__in=exits_ids)
        ]
        if oa_types:
            OAWorkflowType.objects.bulk_create(
                oa_types,
                update_conflicts=True,
                update_fields=["workflow_type_name", "desc", "order", "uuid"],
                unique_fields=["workflow_type_id"],
            )

    def changelist_view(self, request, extra_context=None):
        # 从销售系统导入数据到ProductBusinessDataTemp表
        if request.GET.get("import", "") == "true":
            self.import_data(request, request.GET.get("type_id"))
            self.message_user(request, "目录已导入", level=messages.SUCCESS)
        # 把ProductBusinessDataTemp表数据 upsert 到ProductBusinessData表
        elif request.GET.get("sync", "") == "true":
            self.upsert_data(request)
            self.message_user(request, "同步成功", level=messages.SUCCESS)

        # 获取OA流程目录
        result = WorkflowType.objects.values("ID", "TYPENAME").order_by("DSPORDER")
        exits_type_ids = list(
            OAWorkflowType.objects.values_list("workflow_type_id", flat=True)
        )
        for i in result:
            i["disabled"] = i["ID"] in exits_type_ids
        if extra_context:
            extra_context["oa_workflow_types"] = result
        else:
            extra_context = {"oa_workflow_types": result}

        return super().changelist_view(request, extra_context=extra_context)


class WorkFlowForm(forms.ModelForm):
    file_category_id = form_fields.IntegerField(required=False)
    category = form_fields.IntegerField(required=False)

    class Meta:
        model = OAWorkflow
        fields = "__all__"  # noqa: DJ007


class WorkFlowNodeInline(admin.TabularInline):
    can_delete = False
    model = OAWorkflowNode
    # autocomplete_fields = ["permissions"]
    verbose_name = "流程节点"
    verbose_name_plural = "流程节点"
    ordering = ("status", "-is_start", "is_end", "node_order")
    exclude = ("permissions",)
    readonly_fields = [
        "status",
        "oa_workflow",
        "workflow_id",
        "node_order",
        "node_id",
        "node_name",
        "is_start",
        "is_reject",
        "is_reopen",
        "is_end",
    ]

    def has_add_permission(self, *args, **kwargs):
        return False

    class Media:
        css = {"all": ("css/hide_admin_original.css",)}


class WorkFlowEdgeInline(admin.TabularInline):
    can_delete = False
    model = OAWorkflowEdge
    verbose_name = "流程节点关系"
    verbose_name_plural = "流程节点关系"
    ordering = ("from_node_id", "-from_node_name", "to_node_id", "to_node_name")

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_change_permission(self, *args, **kwargs):
        return False

    class Media:
        css = {"all": ("css/hide_admin_original.css",)}


@admin.register(OAWorkflow)
class OAWorkflowAdmin(admin.ModelAdmin):
    form = WorkFlowForm
    list_display = (
        "id",
        "name",
        "workflow_id",
        "workflow_type_id",
        "order",
        "workflow_version",
        "code",
        "status",
    )
    change_form_template = "drf_oa_workflow/workflowChange.html"
    change_list_template = "drf_oa_workflow/workflowList.html"
    actions = []
    list_display_links = ("name",)
    readonly_fields = (
        # "status",
        # "name",
        "parent",
        "active_version",
        "workflow_type_id",
        "workflow_form_id",
        # "workflow_main_table",
        "workflow_version",
        "is_active_version",
        "order",
    )
    inlines = [
        WorkFlowNodeInline,
        WorkFlowEdgeInline,
    ]
    search_fields = ("code", "name")
    search_help_text = "输入流程名称或编号以查找"
    ordering = ("workflow_type_id", "order")

    def has_add_permission(self, request):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        try:
            chat_url = self.get_object(request, object_id).chart_url
            get_chat_error = None
        except Exception as e:
            chat_url = ""
            get_chat_error = str(e)
        extra_context["workflowChatUrl"] = chat_url
        extra_context["getChatError"] = get_chat_error
        return super().change_view(
            request, object_id, form_url=form_url, extra_context=extra_context
        )

    def response_change(self, request, obj):
        # 同步Oa中的节点以及搞关系
        if "_sync_flow_nodes" in request.POST:
            self.process_sync_flow_nodes(obj)
            self.message_user(request, "已从OA同步流程信息")
            return HttpResponseRedirect(request.path)
        return super().response_change(request, obj)

    def process_sync_flow_nodes(self, obj):
        """
        同步OA中此流程的节点
        """
        obj.sync_nodes_from_oa()
        obj.sync_node_relations_from_oa()
        if obj.workflow_version == 1 or not obj.workflow_version:
            obj.sync_other_versions(obj.workflow_id)

    def changelist_view(self, request, extra_context=None):
        action = request.GET.get("action", "")
        # 从OA导入流程
        if action == "import":
            oa_workflow_id = str(request.GET["workflowId"])
            if not oa_workflow_id.isdigit():
                self.message_user(request, "OA流程ID格式错误", level=messages.WARNING)
            else:
                OAWorkflow.sync_other_versions(oa_workflow_id)
                wf_class = OAWorkflow.objects.filter(
                    workflow_id=int(oa_workflow_id)
                ).first()
                if wf_class:
                    wf_class.sync_nodes_from_oa()
                    wf_class.sync_node_relations_from_oa()
                    self.message_user(request, "流程已导入", level=messages.SUCCESS)
                else:
                    self.message_user(
                        request,
                        f"OA中不存在ID为'{oa_workflow_id}'的流程",
                        level=messages.WARNING,
                    )
        elif action == "sync":
            OAWorkflow.sync_other_versions()
            self.message_user(request, "同步成功", level=messages.SUCCESS)

        # 获取OA流程
        exits_type_ids = list(
            OAWorkflowType.objects.values_list("workflow_type_id", flat=True)
        )
        exits_wf_ids = list(OAWorkflow.objects.values_list("workflow_id", flat=True))
        result = (
            WorkflowBase.objects.select_related("WORKFLOWTYPE")
            .extra(select={"DSPORDER": "ECOLOGY.WORKFLOW_BASE.DSPORDER"})
            .filter(WORKFLOWTYPE_id__in=exits_type_ids)
            .exclude(ID__in=exits_wf_ids)
            .exclude(ISTEMPLATE="1")
            .annotate(
                id=F("ID"),
                name=F("WORKFLOWNAME"),
                type_name=F("WORKFLOWTYPE__TYPENAME"),
            )
            .values("id", "name", "type_name")
            .order_by("WORKFLOWTYPE__DSPORDER", "DSPORDER")
        )
        # for i in result:
        #     i["disabled"] = i["id"] in exits_wf_ids
        if extra_context:
            extra_context["oa_workflows"] = result
        else:
            extra_context = {"oa_workflows": result}

        return super().changelist_view(request, extra_context=extra_context)
