from django.db.models import Prefetch
from rest_framework import serializers

from drf_oa_workflow.models import OAWorkflow
from drf_oa_workflow.models import OAWorkflowEdge
from drf_oa_workflow.models import OAWorkflowNode
from drf_oa_workflow.models import WorkflowApproval
from drf_oa_workflow.utils import get_sync_oa_user_model

OAUserModel = get_sync_oa_user_model()


class WorkFlowNodeSerializer(serializers.ModelSerializer):
    can_return = serializers.BooleanField(default=False, label="可退回")

    class Meta:
        model = OAWorkflowNode
        exclude = ("oa_workflow", "permissions")


class OAWorkflowSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = OAWorkflow
        exclude = ("created_by", "updated_by")


class WorkflowApprovalSerializer(serializers.ModelSerializer):
    # 审核单基础信息->前端用
    id = serializers.IntegerField(label="ID", read_only=True)
    code = serializers.CharField(label="流程编码", read_only=True)
    title = serializers.CharField(label="流程标题", read_only=True)
    front_form_info = serializers.JSONField(label="流程表单信息(前端)", read_only=True)
    workflow_request_id = serializers.CharField(label="OA流程实例ID", read_only=True)
    oa_workflow_code = serializers.CharField(
        label="OA流程编码", source="workflow.code", read_only=True
    )

    class Meta:
        model = WorkflowApproval
        fields = [
            "id",
            "code",
            "title",
            "front_form_info",
            "workflow_request_id",
            "oa_workflow_code",
        ]


class WFListApprovalSerializer(serializers.ModelSerializer):
    code = serializers.CharField(help_text="流程编号(废弃)")
    title = serializers.CharField(help_text="流程标题(废弃)")
    workflow_code = serializers.CharField(
        source="workflow.code", help_text="流程类型编号"
    )
    workflow_name = serializers.CharField(
        source="workflow.name", help_text="流程类型名称"
    )
    oa_request_id = serializers.CharField(
        source="workflow_request_id", help_text="OA流程RequestID"
    )
    oa_workflow_id = serializers.IntegerField(
        source="workflow.workflow_id", label="OA流程类型ID"
    )
    workflow_main_table = serializers.CharField(
        source="workflow.workflow_main_table", help_text="OA流程主表"
    )
    workflow_detail_tables = serializers.ListField(
        source="workflow.workflow_detail_tables",
        child=serializers.CharField(),
        help_text="OA流程子表",
    )
    file_category_id = serializers.IntegerField(
        source="workflow.file_category_id", help_text="OA流程文件目录ID"
    )
    data_type = serializers.SerializerMethodField(help_text="本系统数据类型")
    data_id = serializers.CharField(source="object_id", help_text="本系统数据ID")

    @classmethod
    def process_queryset(cls, request, queryset):
        return queryset.select_related("workflow", "content_type")

    def get_data_type(self, instance):
        return f"{instance.content_type.app_label}.{instance.content_type.model}"

    class Meta:
        model = WorkflowApproval
        fields = (
            "code",
            "title",
            "workflow_code",
            "workflow_name",
            "oa_request_id",
            "oa_workflow_id",
            "workflow_main_table",
            "workflow_detail_tables",
            "file_category_id",
            "data_type",
            "data_id",
            "approval_status",
            "front_form_info",
        )


class WFApprovalSerializer(serializers.ModelSerializer):
    workflow = OAWorkflowSimpleSerializer(read_only=True, label="流程信息")

    @classmethod
    def process_queryset(cls, request, queryset):
        return queryset.select_related(
            "workflow", "content_type", "created_by", "updated_by"
        )

    class Meta:
        model = WorkflowApproval
        fields = "__all__"


class WFApprovalDetailSerializer(WFApprovalSerializer):
    workflow_nodes = WorkFlowNodeSerializer(
        source="workflow.flow_nodes", many=True, read_only=True
    )

    @classmethod
    def process_queryset(cls, request, queryset):
        return queryset.select_related("workflow", "created_by").prefetch_related(
            Prefetch(
                "workflow__flow_node_relations",
                queryset=OAWorkflowEdge.objects.select_related("to_node").all(),
            ),
            Prefetch(
                "workflow__flow_nodes",
                queryset=OAWorkflowNode.objects.valid().order_by(
                    "-is_start", "is_end", "node_order"
                ),
            ),
        )

    class Meta:
        model = WorkflowApproval
        exclude = ("content_type", "object_id", "updated_by")
