from django.db.models import Prefetch
from rest_framework import serializers

from drf_oa_workflow.models import Approval
from drf_oa_workflow.models import RegisterWorkflow
from drf_oa_workflow.models import RegisterWorkflowEdge
from drf_oa_workflow.models import RegisterWorkflowNode
from drf_oa_workflow.service import WFService
from drf_oa_workflow.utils import get_sync_oa_user_model

from .workflow_register import RegisterWorkflowNodeExtSerializer

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


class WFApprovalSerializer(serializers.ModelSerializer):
    data_type = serializers.SerializerMethodField(help_text="本系统单据")
    data_id = serializers.IntegerField(source="object_id", help_text="本系统单据ID")

    @classmethod
    def get_data_type(cls, instance):
        return f"{instance.content_type.app_label}.{instance.content_type.model}"

    @classmethod
    def process_queryset(cls, request, queryset):
        return queryset.select_related("content_type")

    class Meta:
        model = Approval
        fields = [
            "id",
            "data_type",
            "data_id",
            "workflow_request_id",
            "approval_status",
            "action",
            "created_at",
            "updated_at",
            "archived_at",
            "front_form_info",
        ]


class WFApprovalDetailSerializer(WFApprovalSerializer):
    register_workflow = OAWorkflowSimpleSerializer(read_only=True, label="流程信息")
    workflow_nodes = RegisterWorkflowNodeExtSerializer(
        source="register_workflow.flow_nodes", many=True, read_only=True
    )
    can_edit = serializers.BooleanField(
        default=False, read_only=True, label="是否可编辑"
    )
    current_node_id = serializers.IntegerField(
        default=None, read_only=True, label="当前节点ID"
    )
    oa_workflow_detail = serializers.DictField(
        default={}, read_only=True, label="OA流程信息"
    )
    passed_nodes = serializers.ListField(default=[], read_only=True, label="已经过节点")

    @classmethod
    def process_queryset(cls, request, queryset):
        return queryset.select_related(
            "content_type", "register_workflow"
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

    def to_representation(self, instance):
        result = super().to_representation(instance)
        # 获取流程信息
        # 是否可编辑、当前节点等
        can_edit, current_node_id, handled_detail = WFService.get_oa_workflow_info(
            instance, self.context["request"].user
        )

        # 设置可退回节点
        wf_passed_nodes = []
        if handled_detail["buttons"]["return"]:
            wf_passed_nodes = WFService.get_oa_wf_passed_nodes(
                instance.workflow_request_id
            )
            passed_nodes = WFService.can_return_oa_nodes(
                instance, current_node_id, wf_passed_nodes
            )
            for i in result["workflow_nodes"]:
                if i["node_id"] in passed_nodes:
                    i["can_return"] = True
        result.update(
            {
                "can_edit": can_edit,
                "current_node_id": current_node_id,
                "passed_nodes": wf_passed_nodes,
                "oa_workflow_detail": handled_detail,
            }
        )
        return result

    class Meta:
        model = Approval
        fields = [
            "id",
            "data_type",
            "data_id",
            "register_workflow",
            "workflow_nodes",
            "can_edit",
            "current_node_id",
            "oa_workflow_detail",
            "passed_nodes",
            "workflow_request_id",
            "approval_status",
            "action",
            "created_at",
            "updated_at",
            "archived_at",
            "front_form_info",
        ]
