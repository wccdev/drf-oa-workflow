from django.db.models import Prefetch
from rest_framework import serializers

from drf_oa_workflow.models import Approval
from drf_oa_workflow.models import RegisterWorkflow
from drf_oa_workflow.models import RegisterWorkflowEdge
from drf_oa_workflow.models import RegisterWorkflowNode
from drf_oa_workflow.utils import get_sync_oa_user_model

from .workflow_register import RegisterWorkflowNodeSerializer

OAUserModel = get_sync_oa_user_model()


class OAWorkflowSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegisterWorkflow
        fields = [
            "id",
            "code",
            "name",
            "workflow_id",
            "workflow_type_id",
            "workflow_form_id",
            "workflow_main_table",
            "is_active_version",
            "workflow_version",
            "file_category_id",
            "remark",
        ]


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
        model = Approval
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
        source="register_workflow.code", help_text="流程类型编号"
    )
    workflow_name = serializers.CharField(
        source="register_workflow.name", help_text="流程类型名称"
    )
    oa_request_id = serializers.CharField(
        source="workflow_request_id", help_text="OA流程RequestID"
    )
    register_workflow_id = serializers.IntegerField(
        source="register_workflow.workflow_id", label="OA流程类型ID"
    )
    workflow_main_table = serializers.CharField(
        source="register_workflow.workflow_main_table", help_text="OA流程主表"
    )
    workflow_detail_tables = serializers.ListField(
        source="register_workflow.workflow_detail_tables",
        child=serializers.CharField(),
        help_text="OA流程子表",
    )
    file_category_id = serializers.IntegerField(
        source="register_workflow.file_category_id", help_text="OA流程文件目录ID"
    )
    data_type = serializers.SerializerMethodField(help_text="本系统数据类型")
    data_id = serializers.CharField(source="object_id", help_text="本系统数据ID")

    @classmethod
    def process_queryset(cls, request, queryset):
        return queryset.select_related("register_workflow", "content_type")

    def get_data_type(self, instance):
        return f"{instance.content_type.app_label}.{instance.content_type.model}"

    class Meta:
        model = Approval
        fields = (
            "code",
            "title",
            "workflow_code",
            "workflow_name",
            "oa_request_id",
            "register_workflow_id",
            "workflow_main_table",
            "workflow_detail_tables",
            "file_category_id",
            "data_type",
            "data_id",
            "approval_status",
            "front_form_info",
        )


class WFApprovalSerializer(serializers.ModelSerializer):
    register_workflow = OAWorkflowSimpleSerializer(read_only=True, label="流程信息")

    @classmethod
    def process_queryset(cls, request, queryset):
        return queryset.select_related(
            "register_workflow", "content_type", "created_by", "updated_by"
        )

    class Meta:
        model = Approval
        fields = "__all__"


class WFApprovalDetailSerializer(WFApprovalSerializer):
    register_workflow_nodes = RegisterWorkflowNodeSerializer(
        source="register_workflow.flow_nodes", many=True, read_only=True
    )

    @classmethod
    def process_queryset(cls, request, queryset):
        return queryset.select_related(
            "register_workflow", "created_by"
        ).prefetch_related(
            Prefetch(
                "register_workflow__flow_node_relations",
                queryset=RegisterWorkflowEdge.objects.select_related("to_node").all(),
            ),
            Prefetch(
                "register_workflow__flow_nodes",
                queryset=RegisterWorkflowNode.objects.order_by(
                    "-is_start", "is_end", "node_order"
                ),
            ),
        )

    class Meta:
        model = Approval
        exclude = ("content_type", "object_id", "updated_by")
