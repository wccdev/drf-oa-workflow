from rest_framework import serializers

from drf_oa_workflow.choices import TransmitTypes
from drf_oa_workflow.choices import WFOperationTypes


class WFBaseDataSerializer(serializers.Serializer):
    oa_node_id = serializers.IntegerField(
        required=True, allow_null=False, label="当前流程节点ID"
    )
    remark = serializers.CharField(
        allow_null=True, allow_blank=True, required=False, default="", label="意见"
    )


class WFReviewDataSerializer(WFBaseDataSerializer):
    review_type = serializers.ChoiceField(
        required=True,
        choices=(
            (WFOperationTypes.APPROVAL.value, WFOperationTypes.APPROVAL.label),
            (WFOperationTypes.MARKUP.value, WFOperationTypes.MARKUP.label),
            (WFOperationTypes.RE_SUBMIT.value, WFOperationTypes.RE_SUBMIT.label),
        ),
        label="审核类型",
    )
    post_data = serializers.DictField(required=False)


class WFTransmitDataSerializer(WFBaseDataSerializer):
    trans_type = serializers.ChoiceField(
        required=True, choices=TransmitTypes, label="审核类型"
    )
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        allow_empty=False,
        label="用户IDS",
    )


class WFRejectDataSerializer(WFBaseDataSerializer):
    reject_node_id = serializers.IntegerField(
        required=False, allow_null=True, label="指定退回流程节点ID"
    )
