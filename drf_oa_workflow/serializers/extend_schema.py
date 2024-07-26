from rest_framework import serializers

from drf_oa_workflow.choices import TransmitTypes
from drf_oa_workflow.choices import WFOperationTypes


class WorkflowBaseSubmitSerializer(serializers.Serializer):
    oa_node_id = serializers.IntegerField(
        required=True, allow_null=False, help_text="当前OA节点ID"
    )


class WorkflowReviewSerializer(WorkflowBaseSubmitSerializer):
    remark = serializers.CharField(
        required=True, allow_blank=True, help_text="审批意见(支持富文本)"
    )


class WorkflowReviewDispatchSerializer(WorkflowReviewSerializer):
    review_type = serializers.ChoiceField(
        choices=(
            (WFOperationTypes.APPROVAL.value, WFOperationTypes.APPROVAL.label),
            (WFOperationTypes.MARKUP.value, WFOperationTypes.MARKUP.label),
            (WFOperationTypes.RE_SUBMIT.value, WFOperationTypes.RE_SUBMIT.label),
        ),
        required=True,
        help_text="提交类型",
    )
    post_data = serializers.DictField(
        required=False, allow_null=True, help_text="提交的流程主表数据"
    )


class WorkflowRejectSerializer(WorkflowReviewSerializer):
    reject_node_id = serializers.IntegerField(
        required=False, allow_null=True, help_text="指定退回的OA流程节点ID"
    )


class WorkflowTransmitSerializer(WorkflowReviewSerializer):
    trans_type = serializers.ChoiceField(
        choices=TransmitTypes.choices, required=True, help_text="转发类型"
    )
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        allow_empty=False,
        allow_null=False,
        help_text="本系统接收人ID",
    )


class WorkflowWithdrawSerializer(WorkflowReviewSerializer):
    remind = serializers.ChoiceField(
        required=True, choices=(("0", "不提醒"), ("1", "提醒")), help_text="是否提醒"
    )


class OAWorkFlowFrontSerializer(serializers.Serializer):
    """
    OA流程前端表单提交数据
    流程中提交数据的参数{"oa_workflow_front":{"current_node_id":70557}}
    """

    current_node_id = serializers.IntegerField(
        help_text="流程节点id", required=True, write_only=True
    )

    class Meta:
        fields = ("current_node_id",)
