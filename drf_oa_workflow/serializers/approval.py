# ruff: noqa: N815
from __future__ import annotations

from itertools import groupby

from rest_framework import serializers

from drf_oa_workflow.models import WorkflowBase
from drf_oa_workflow.models import WorkflowCurrentOperator
from drf_oa_workflow.models import WorkflowRequestBase


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


class WorkflowBaseSerializer(serializers.ModelSerializer):
    workflowId = serializers.IntegerField(source="ID", read_only=True, label="流程ID")
    workflowName = serializers.CharField(
        source="WORKFLOWNAME", read_only=True, label="流程类型"
    )

    class Meta:
        model = WorkflowBase
        fields = ("workflowId", "workflowName", "FORMID")


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
    unOperators = serializers.CharField(default="", read_only=True, label="未操作者")

    workflowBaseInfo = WorkflowBaseSerializer(
        source="WORKFLOWID", default=None, read_only=True
    )

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
            "workflowBaseInfo",
        )
        list_serializer_class = WFListSerializer
