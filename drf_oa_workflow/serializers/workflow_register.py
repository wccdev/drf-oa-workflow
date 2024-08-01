from rest_framework import serializers

from drf_oa_workflow.models import RegisterWorkflow
from drf_oa_workflow.models import RegisterWorkflowEdge
from drf_oa_workflow.models import RegisterWorkflowNode


class RegisterWorkflowNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegisterWorkflowNode
        exclude = ("register_workflow",)


class RegisterWorkflowNodeExtSerializer(serializers.ModelSerializer):
    can_return = serializers.BooleanField(default=False, label="可退回")

    class Meta:
        model = RegisterWorkflowNode
        exclude = ("register_workflow",)


class RegisterWorkflowEdgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegisterWorkflowEdge
        fields = [
            "id",
            "from_node_id",
            "from_node_name",
            "to_node_id",
            "to_node_name",
            "link_name",
        ]


class RegisterWorkflowSerializer(serializers.ModelSerializer):
    workflow_type_name = serializers.CharField(
        source="workflow_type.workflow_type_name", read_only=True, label="流程目录"
    )
    workflow_detail_tables = serializers.ListField(
        child=serializers.CharField(), label="OA子表"
    )
    tree_path = serializers.SerializerMethodField(read_only=True, label="Path")

    def get_tree_path(self, instance):
        tree_path = [instance.workflow_id]
        if instance.parent_id:
            tree_path.insert(0, instance.parent_id)
        return tree_path

    class Meta:
        model = RegisterWorkflow
        exclude = ("parent", "active_version")


class RegisterWorkflowRetrieveSerializer(RegisterWorkflowSerializer):
    flow_nodes = RegisterWorkflowNodeSerializer(
        many=True, read_only=True, label="流程节点"
    )
    flow_node_relations = RegisterWorkflowEdgeSerializer(
        many=True, read_only=True, label="流程节点关系"
    )
    chart_url = serializers.SerializerMethodField(
        read_only=True, default="", label="流程图链接"
    )

    def get_chart_url(self, instance):
        return instance.chart_url


class RegisterWorkflowSaveSerializer(serializers.ModelSerializer):
    code = serializers.CharField(
        required=True, allow_blank=False, allow_null=False, label="流程编号"
    )
    workflow_detail_tables = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        label="OA流程子表",
    )

    class Meta:
        model = RegisterWorkflow
        fields = (
            "code",
            "name",
            "workflow_id",
            "workflow_main_table",
            "workflow_detail_tables",
            "file_category_id",
            "status",
            "remark",
            "form_permissions",
        )
