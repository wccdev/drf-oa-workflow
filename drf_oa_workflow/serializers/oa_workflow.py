# ruff: noqa: N815
from __future__ import annotations

from itertools import groupby

from rest_framework import serializers

from drf_oa_workflow.choices import ApprovalStatus
from drf_oa_workflow.choices import DocStatus
from drf_oa_workflow.choices import WFOperationTypes
from drf_oa_workflow.models import WorkflowApprovalOperation
from drf_oa_workflow.models import WorkflowBase
from drf_oa_workflow.models import WorkflowCurrentOperator
from drf_oa_workflow.models import WorkflowRequestBase
from drf_oa_workflow.models import WorkflowRequestLog


class WorkflowBaseSerializer(serializers.ModelSerializer):
    workflowId = serializers.IntegerField(source="ID", read_only=True, label="流程ID")
    workflowName = serializers.CharField(
        source="WORKFLOWNAME", read_only=True, label="流程类型"
    )

    class Meta:
        model = WorkflowBase
        fields = ("workflowId", "workflowName", "FORMID")


class WFListSerializer(serializers.ListSerializer):
    @classmethod
    def match_un_operators(cls, datas: list[dict | WorkflowRequestBase]):
        """
        获取流程对应的未操作人
        """
        request_logs = (
            WorkflowCurrentOperator.objects.wf_un_operators()
            .filter(
                REQUESTID_id__in=[
                    int(i["requestId"] if isinstance(i, dict) else i.REQUESTID)
                    for i in datas
                ]
            )
            .values("request_id", "un_operator_id", "un_operator_name")
            .order_by("request_id")
        )
        operators_map = {}
        for request_id, logs in groupby(request_logs, key=lambda x: x["request_id"]):
            logs = list(logs)  # noqa: PLW2901
            if logs:
                operators_map[str(request_id)] = ",".join(
                    [i["un_operator_name"] for i in logs]
                )
            else:
                operators_map[str(request_id)] = ""

        for i in datas:
            if isinstance(i, dict):
                i["unOperators"] = operators_map.get(str(i["requestId"]), "")
            else:
                i.unOperators = operators_map.get(str(i.REQUESTID), "")

        return datas

    def to_representation(self, data):
        return super().to_representation(self.match_un_operators(data))


class TodoHandledListSerializer(serializers.ModelSerializer):
    requestId = serializers.IntegerField(
        source="REQUESTID", read_only=True, label="流程请求ID"
    )
    requestmark = serializers.CharField(
        source="REQUESTMARK", read_only=True, label="流程编号"
    )
    requestName = serializers.CharField(
        source="REQUESTNAME", read_only=True, label="流程标题"
    )
    requestLevel = serializers.IntegerField(
        source="REQUESTLEVEL", read_only=True, label="紧急度"
    )
    currentNodeId = serializers.IntegerField(
        source="CURRENTNODEID_id", read_only=True, label="当前节点ID"
    )
    currentNodeName = serializers.CharField(
        source="CURRENTNODEID.NODENAME", read_only=True, label="当前节点"
    )
    status = serializers.CharField(source="STATUS", read_only=True, label="流程状态")
    creatorId = serializers.IntegerField(
        source="CREATER_id", read_only=True, label="创建人ID"
    )
    creatorName = serializers.CharField(
        source="CREATER.LASTNAME", read_only=True, label="创建人"
    )
    lastOperatorId = serializers.IntegerField(
        source="LASTOPERATOR_id", read_only=True, label="最后操作人ID"
    )
    lastOperatorName = serializers.CharField(
        source="LASTOPERATOR.LASTNAME", read_only=True, label="最后操作人"
    )
    isreject = serializers.CharField(source="C_ISREJECT", read_only=True)
    isbereject = serializers.CharField(
        source="C_ISBEREJECT", read_only=True, label="是否被退回"
    )
    createTime = serializers.DateTimeField(read_only=True, label="创建时间")
    receiveTime = serializers.DateTimeField(read_only=True, label="接收时间")
    lastOperateTime = serializers.DateTimeField(read_only=True, label="最后操作时间")
    viewtype = serializers.IntegerField(
        source="C_VIEWTYPE", read_only=True, label="查看"
    )
    isremark = serializers.IntegerField(source="C_ISREMARRK", read_only=True)
    nodeid = serializers.IntegerField(source="C_NODEID", read_only=True, label="节点ID")
    # workflowId = serializers.IntegerField(source="WORKFLOWID_id", read_only=True)
    unOperators = serializers.CharField(default="", read_only=True, label="未操作者")
    approval_status = serializers.ChoiceField(
        source="extend_info.APPROVAL_STATUS",
        choices=ApprovalStatus.choices,
        label="审批状态",
    )
    doc_status = serializers.ChoiceField(
        source="extend_info.DOC_STATUS", choices=DocStatus.choices, label="单据状态"
    )

    workflowBaseInfo = WorkflowBaseSerializer(
        source="WORKFLOWID", default=None, read_only=True
    )
    workflowConf = serializers.DictField(default=None, read_only=True)

    @classmethod
    def process_queryset(cls, request, queryset):
        return queryset.select_related(
            "CREATER", "LASTOPERATOR", "CURRENTNODEID", "WORKFLOWID", "extend_info"
        ).distinct()

    class Meta:
        model = WorkflowRequestBase
        fields = (
            "requestId",
            "requestmark",
            "requestName",
            "requestLevel",
            "currentNodeId",
            "currentNodeName",
            "status",
            "creatorId",
            "creatorName",
            "lastOperatorId",
            "lastOperatorName",
            "isreject",
            "isbereject",
            "createTime",
            "receiveTime",
            "lastOperateTime",
            "viewtype",
            "isremark",
            "nodeid",
            # "workflowId",
            "unOperators",
            "approval_status",
            "doc_status",
            "workflowBaseInfo",
            "workflowConf",
        )
        list_serializer_class = WFListSerializer


class WFRequestLogCusListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        result = super().to_representation(data)

        # 替换审批拒绝操作记录的显示
        terminate_log_ids = WorkflowApprovalOperation.objects.filter(
            oa_log_id__in=[i["id"] for i in result]
        ).values_list("oa_log_id", flat=True)
        for i in result:
            if i["id"] in terminate_log_ids:
                i["operateType"] = WFOperationTypes.TERMINATE.label
        return result


class WorkflowRequestLogSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="LOGID", read_only=True)
    logtype = serializers.CharField(source="LOGTYPE", read_only=True)
    nodeid = serializers.IntegerField(source="NODEID_id", read_only=True)
    nodename = serializers.CharField(source="NODEID.NODENAME", read_only=True)
    operatedate = serializers.CharField(source="OPERATEDATE", read_only=True)
    operatetime = serializers.CharField(source="OPERATETIME", read_only=True)
    operator = serializers.IntegerField(source="OPERATOR_id", read_only=True)
    operatorName = serializers.CharField(source="OPERATOR.LASTNAME", read_only=True)
    operatorDept = serializers.IntegerField(
        source="OPERATOR.DEPARTMENTID_id", read_only=True
    )
    operatorDeptName = serializers.CharField(
        source="OPERATOR.DEPARTMENTID.DEPARTMENTNAME", read_only=True
    )
    operateType = serializers.CharField(source="get_LOGTYPE_display", read_only=True)
    remarkHtml = serializers.CharField(source="REMARK", read_only=True)
    receivedPersonids = serializers.CharField(
        source="RECEIVEDPERSONIDS", read_only=True
    )
    receivedPersons = serializers.CharField(source="RECEIVEDPERSONS", read_only=True)

    class Meta:
        model = WorkflowRequestLog
        fields = (
            "id",
            "logtype",
            "nodeid",
            "nodename",
            "operatedate",
            "operatetime",
            "operator",
            "operatorName",
            "operatorDept",
            "operatorDeptName",
            "operateType",
            "remarkHtml",
            "receivedPersonids",
            "receivedPersons",
        )
        list_serializer_class = WFRequestLogCusListSerializer
