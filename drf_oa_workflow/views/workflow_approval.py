import base64
import hashlib
import json
import re

import django_filters
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.db.transaction import atomic
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.utils import extend_schema
from drfexts.viewsets import ExtGenericViewSet
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import ListModelMixin
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.response import Response

from drf_oa_workflow.choices import ApprovalStatus
from drf_oa_workflow.choices import TransmitTypes
from drf_oa_workflow.choices import WFOperationTypes
from drf_oa_workflow.contains import DEFAULT_MAIN_DATA
from drf_oa_workflow.contains import TERMINATE_COLUMN
from drf_oa_workflow.contains import TERMINATE_MAIN_DATA
from drf_oa_workflow.mixin import OaWFApiViewMixin
from drf_oa_workflow.models import Approval
from drf_oa_workflow.models import OaUserInfo
from drf_oa_workflow.models import RegisterWorkflow
from drf_oa_workflow.models import RegisterWorkflowNode
from drf_oa_workflow.models import WorkflowRequestBase
from drf_oa_workflow.models import WorkflowRequestLog
from drf_oa_workflow.models import WorkflowRequestWccExtendInfo
from drf_oa_workflow.serializers.extend_schema import WorkflowBaseSubmitSerializer
from drf_oa_workflow.serializers.extend_schema import WorkflowRejectSerializer
from drf_oa_workflow.serializers.extend_schema import WorkflowReviewDispatchSerializer
from drf_oa_workflow.serializers.extend_schema import WorkflowReviewSerializer
from drf_oa_workflow.serializers.extend_schema import WorkflowTransmitSerializer
from drf_oa_workflow.serializers.extend_schema import WorkflowWithdrawSerializer
from drf_oa_workflow.serializers.oa_workflow import TodoHandledListSerializer
from drf_oa_workflow.serializers.oa_workflow import WorkflowRequestLogSerializer
from drf_oa_workflow.serializers.post_data_valid import WFBaseDataSerializer
from drf_oa_workflow.serializers.post_data_valid import WFRejectDataSerializer
from drf_oa_workflow.serializers.post_data_valid import WFReviewDataSerializer
from drf_oa_workflow.serializers.post_data_valid import WFTransmitDataSerializer
from drf_oa_workflow.serializers.user import WorkFlowUserSerializer
from drf_oa_workflow.serializers.workflow_approval import WFApprovalDetailSerializer
from drf_oa_workflow.serializers.workflow_approval import WFApprovalSerializer
from drf_oa_workflow.serializers.workflow_register import RegisterWorkflowNodeSerializer
from drf_oa_workflow.serializers.workflow_register import (
    RegisterWorkFlowNodeSimpleSerializer,
)
from drf_oa_workflow.service import WFService
from drf_oa_workflow.settings import SYSTEM_IDENTIFIER_KEY
from drf_oa_workflow.utils import OaWorkflowApi
from drf_oa_workflow.utils import get_sync_oa_user_model

User = get_user_model()
OaUserModel: OaUserInfo = get_sync_oa_user_model()


def filter_workflow(qs, name, value):
    ids = list(
        RegisterWorkflow.objects.filter(
            Q(id=int(value)) | Q(parent__id=int(value))
        ).values_list("workflow_id", flat=True)
    )
    return qs.filter(WORKFLOWID_id__in=ids)


class WorkflowsViewSet(OaWFApiViewMixin, ListModelMixin, ExtGenericViewSet):
    queryset = WorkflowRequestBase.objects.filter(
        extend_info__SOURCE=settings.DRF_OA_WORKFLOW[SYSTEM_IDENTIFIER_KEY]
    ).all()
    serializer_class = TodoHandledListSerializer
    ordering = ("-lastOperateTime",)

    filterset_fields_overwrite = {
        "workflowBaseInfo.workflowId": django_filters.NumberFilter(
            method=filter_workflow
        ),
    }
    search_fields = ["REQUESTMARK", "REQUESTNAME", "WORKFLOWID__WORKFLOWNAME"]

    @classmethod
    def get_essential_factor(cls, request):
        try:
            oa_user_id = request.user.oa_user_id
        except APIException:
            oa_user_id = None
        workflow_ids = list(
            RegisterWorkflow.objects.values_list("workflow_id", flat=True)
        )

        return oa_user_id, workflow_ids

    def _list(self, queryset):
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="list_target",
                location=OpenApiParameter.QUERY,
                required=True,
                description="请求流程类型[todo: 待办; handled: 已办]",
                enum=["todo", "handled"],
                type=OpenApiTypes.STR,
                default="todo",
                allow_blank=False,
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        oa_user_id, workflow_ids = self.get_essential_factor(request)
        if not oa_user_id or not workflow_ids:
            return Response()

        list_target = request.GET.get("list_target", "todo") or "todo"
        if list_target == "todo":
            self.ordering = ("-receiveTime",)
            queryset = self.get_queryset().todo(oa_user_id, workflow_ids)
        else:
            queryset = self.get_queryset().handled(oa_user_id, workflow_ids)
        return self._list(self.filter_queryset(queryset))


class WorkflowApprovalViewSet(
    OaWFApiViewMixin, ListModelMixin, RetrieveModelMixin, ExtGenericViewSet
):
    queryset = Approval.objects.all()
    serializer_class = {
        "default": WFApprovalSerializer,
        "retrieve": WFApprovalDetailSerializer,
    }
    lookup_field = "workflow_request_id"
    search_fields = ["code", "title", "workflow__name"]

    post_data_serializer_classes = {
        "default": WFBaseDataSerializer,
        "review": WFReviewDataSerializer,
        "transmit": WFTransmitDataSerializer,
        "reject": WFRejectDataSerializer,
    }

    def get_valid_post_data(self):
        if self.action not in self.post_data_serializer_classes:
            serializer_class = self.post_data_serializer_classes[self._default_key]
        else:
            serializer_class = self.post_data_serializer_classes[self.action]
        serializer = serializer_class(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        return serializer.data

    @extend_schema(request=WorkflowReviewDispatchSerializer)
    @action(detail=True, methods=["POST"])
    def review(self, request, *args, **kwargs):
        """
        批注/重新提交/审核
        """
        approval = self.get_object()
        data = self.get_valid_post_data()
        oa_node_id = data.pop("oa_node_id")
        operation_type = data.pop("review_type")
        post_data: dict = data.pop("post_data", {}) or {}
        post_data.update(DEFAULT_MAIN_DATA)
        post_oa_data = json.dumps(
            [
                {"fieldName": oa_field, "fieldValue": field_value}
                for oa_field, field_value in post_data.items()
            ]
        )
        # TODO 需要提交的OA主表或子表数据
        extras = {"mainData": post_oa_data, "detailData": ""}
        workflow = request.oa_wf_api
        res = workflow.review(
            approval.workflow_request_id, remark=data["remark"], extras=extras
        )
        approval.record_operation(
            request.user, oa_node_id, operation_type, remark=data["remark"]
        )
        return Response(res)

    @extend_schema(request=WorkflowBaseSubmitSerializer)
    @action(detail=True, methods=["POST"])
    def delete(self, request, *args, **kwargs):
        """
        删除流程
          -- OA功能实践，退回到创建节点可删除流程
          -- 注意，需要OA在后台流程配置开启对应功能
          -- 后端应用中心 > 流程引擎 > 路径管理 > 路径设置 > ${找到相关流程} >
             基础设置 > 功能设置 > 退回到创建节点可删除流程 开启
        """
        approval = self.get_object()
        # 当前节点
        data = self.get_valid_post_data()
        oa_node_id = data.pop("oa_node_id")
        res = request.oa_wf_api.delete(approval.workflow_request_id)
        # 删除流程后
        approval.content_object.cancel()
        approval.record_operation(request.user, oa_node_id, WFOperationTypes.DO_DELETE)
        return Response(res)

    @extend_schema(request=WorkflowReviewSerializer)
    @action(detail=True, methods=["POST"])
    def terminate(self, request, *args, **kwargs):
        """
        终止流程
        """
        # raise APIException("终止流程功能暂不开放")
        approval = self.get_object()
        data = self.get_valid_post_data()
        # 当前节点
        oa_node_id = data.pop("oa_node_id")
        # OA流程终止节点需要 流程配置遵循main_data数据内容

        main_data = [
            {"fieldName": k, "fieldValue": v} for k, v in TERMINATE_MAIN_DATA.items()
        ]
        extras = {"mainData": json.dumps(main_data), "detailData": ""}
        workflow = request.oa_wf_api
        res = workflow.review(
            approval.workflow_request_id, remark=data["remark"], extras=extras
        )

        wf_log = (
            WorkflowRequestLog.objects.filter(
                REQUESTID_id=approval.workflow_request_id,
                NODEID_id=oa_node_id,
                OPERATOR_id=request.user.oa_user_id,
                # REMARK=data["remark"]  # 备注
            )
            .order_by("-LOGID")
            .first()
        )
        approval.record_operation(
            request.user,
            oa_node_id,
            WFOperationTypes.TERMINATE,
            oa_log_id=wf_log.LOGID if wf_log else None,
            remark=data["remark"],
        )
        # # 修改OA扩展表状态
        # WorkflowRequestWccExtendInfo.objects.filter(
        #     REQUESTID_id=int(approval.workflow_request_id)
        # ).update(
        #     APPROVAL_STATUS=ApprovalStatus.REJECTED
        # )
        return Response(res)

    @extend_schema(request=WorkflowBaseSubmitSerializer)
    @action(detail=True, methods=["POST"], url_path="force-recover")
    def force_recover(self, request, *args, **kwargs):
        """
        强制收回
          -- OA功能实践，操作人已经审核，且流程在下一个节点还未被审核时，可以强制收回
          -- 注意，需要OA在后台流程配置开启对应功能
          -- 后端应用中心 > 流程引擎 > 路径管理 > 路径设置 > ${找到相关流程} >
             高级设置 > 功能管理 > 节点操作管理
          -- 选择要开启该功能的节点，选择查看前收回或者查看后收回
        """
        workflow = request.oa_wf_api
        data = self.get_valid_post_data()
        oa_node_id = data["oa_node_id"]
        approval = self.get_object()
        res = workflow.recover(approval.workflow_request_id)
        # 强制收回记录
        approval.record_operation(
            request.user, oa_node_id, WFOperationTypes.DO_FORCE_RECOVER
        )
        return Response(res)

    @extend_schema(request=WorkflowWithdrawSerializer)
    @action(detail=True, methods=["POST"])
    def withdraw(self, request, *args, **kwargs):
        """
        流程撤回
          -- OA功能实践
          -- 流程在未归档前都可以被撤回(注意: 此功能会跨越多个节点撤回流程!!！)
          -- 注意，需要OA在后台流程配置开启对应功能
          -- 后端应用中心 > 流程引擎 > 路径管理 > 路径设置 >
             ${找到相关流程} > 高级设置 > 功能管理 > 撤回管理 >
           配置可撤回节点以及节点操作者信息
        """
        # raise APIException("撤回流程功能暂不开放")
        approval = self.get_object()
        data = self.get_valid_post_data()
        # 当前节点
        oa_node_id = data.pop("oa_node_id")

        res = request.oa_wf_api.withdraw(
            approval.workflow_request_id, remark=data["remark"]
        )
        approval.record_operation(
            request.user, oa_node_id, WFOperationTypes.WITHDRAW, remark=data["remark"]
        )
        return Response(res)

    @extend_schema(request=WorkflowTransmitSerializer)
    @action(detail=True, methods=["POST"])
    def transmit(self, request, *args, **kwargs):
        """
        转发、意见征询、转办(对外)
        """
        approval = self.get_object()
        oa_request_id = approval.workflow_request_id
        data = self.get_valid_post_data()
        # 当前节点
        oa_node_id = data.pop("oa_node_id")
        # 1:转发 2:意见征询 3:转办
        trans_type = data["trans_type"]
        # OA用户ID,一个或者多个
        user_id = data["user_ids"]
        oa_user_ids = []
        oa_users_not_found = []
        for u in User.objects.select_related("oauserinfo").filter(pk__in=user_id):
            if hasattr(u, "oauserinfo"):
                oa_user_ids.append(str(u.oauserinfo.user_id))
            else:
                oa_users_not_found.append(u.name)
        if oa_users_not_found:
            us = ".".join([f"'{i}'" for i in oa_users_not_found])
            raise APIException(f"用户{us}无法在OA中使用")
        remark = data["remark"]
        workflow = request.oa_wf_api
        res = workflow.transmit(
            oa_request_id, trans_type, ",".join(oa_user_ids), remark=remark
        )

        if trans_type == TransmitTypes.FORWARD:
            operation_type = WFOperationTypes.FORWARD
        elif trans_type == TransmitTypes.CONSULTATION:
            operation_type = WFOperationTypes.CONSULTATION
        elif trans_type == TransmitTypes.TRANSFER:
            operation_type = WFOperationTypes.TRANSFER
        else:
            raise APIException("‘trans_type’值错误")
        approval.record_operation(
            request.user, oa_node_id, operation_type, remark=remark
        )
        return Response(res)

    @extend_schema(request=WorkflowRejectSerializer)
    @action(detail=True, methods=["POST"])
    def reject(self, request, *args, **kwargs):
        """
        流程退回
        """
        approval = self.get_object()
        data = self.get_valid_post_data()
        # 当前节点
        oa_node_id = data.pop("oa_node_id")
        workflow = request.oa_wf_api
        res = workflow.reject(
            approval.workflow_request_id,
            node_id=data.get("reject_node_id", ""),
            remark=data.get("remark", ""),
        )
        approval.record_operation(
            request.user,
            oa_node_id,
            WFOperationTypes.REJECT,
            remark=data.get("remark", ""),
        )
        return Response(res)

    @action(
        detail=True,
        url_path="oa-remarks",
        serializer_class=WorkflowRequestLogSerializer,
    )
    def oa_remarks_new(self, request, workflow_request_id, *args, **kwargs):
        """
        OA流程流转意见(节点和节点操作信息)
        """

        def match_operator(datas):
            oa_users = OaUserModel.objects.select_related("staff_code").filter(
                user_id__in=[int(i["operator"]) for i in datas]
            )
            user_serializer = WorkFlowUserSerializer(oa_users, many=True)
            oa_user_map = {u["oa_user_id"]: u for u in user_serializer.data}

            for i in datas:
                i["systemUserInfo"] = oa_user_map.get(int(i["operator"]), None)
            return datas

        queryset = (
            WorkflowRequestLog.objects.select_related(
                "NODEID", "OPERATOR", "OPERATOR__DEPARTMENTID"
            )
            .filter(REQUESTID_id=workflow_request_id)
            .order_by("-LOGID")
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(match_operator(serializer.data))

        serializer = self.get_serializer(queryset, many=True)
        return Response(match_operator(serializer.data))

    @action(
        detail=True, url_path="get-operators", serializer_class=WorkFlowUserSerializer
    )
    def get_operators(self, request, *args, **kwargs):
        """
        获取流程当前节点的操作人
        """
        workflow = request.oa_wf_api
        oa_remarks_res = workflow.get_remark(kwargs[self.lookup_field])
        if oa_remarks_res["data"]:
            receiver_ids: str = oa_remarks_res["data"][0]["receivedPersonids"]
            receivers = OaUserModel.objects.select_related("staff_code").filter(
                user_id__in=[int(i) for i in receiver_ids.split(",") if i]
            )
            serializer = self.get_serializer(instance=receivers, many=True)
            return Response(serializer.data)
        return Response()

    @action(detail=True, url_path="chart-url")
    def chat_url(self, request, workflow_request_id, *args, **kwargs):
        """
        流程图链接
        """
        wf_service = request.oa_wf_api
        res = wf_service.get_chart_url(workflow_request_id, request.user.username)
        result = {"host": settings.DRF_OA_WORKFLOW["OA_HOST"], **res["data"]}
        return Response(result)

    def retrieve(self, request, *args, **kwargs):
        """
        流程详细
        """
        # 流程记录
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        result = serializer.data
        return Response(result)

    @action(detail=True, url_path="get-workflow-info")
    def get_workflow_info(self, request, workflow_request_id, *args, **kwargs):
        """
        获取流程的操作按钮、节点等信息
        """
        approval = get_object_or_404(
            self.queryset.select_related("register_workflow"),
            workflow_request_id=workflow_request_id,
        )

        # 流程操作按钮
        can_edit, current_node_id, handled_detail = WFService.get_oa_workflow_info(
            approval, request.user
        )

        # 流程节点
        node_serializer = RegisterWorkFlowNodeSimpleSerializer(
            approval.register_workflow.flow_nodes.all(), many=True
        )
        nodes = node_serializer.data
        wf_passed_nodes = []
        if handled_detail["buttons"]["return"]:
            wf_passed_nodes = WFService.get_oa_wf_passed_nodes(
                approval.workflow_request_id
            )
            passed_nodes = WFService.can_return_oa_nodes(
                approval, current_node_id, wf_passed_nodes
            )
            for i in nodes:
                if i["node_id"] in passed_nodes:
                    i["can_return"] = True

        res = {
            "can_edit": can_edit,
            "current_node_id": current_node_id,
            "wf_passed_nodes": wf_passed_nodes,
            "oa_workflow_detail": handled_detail,
            "workflow_nodes": nodes,
        }
        return Response(res)

    @action(detail=False, url_path=r"get-wf-chart-xml/(?P<wf_id>\d+)")
    def oa_workflow_chat_xml(self, request, wf_id, *args, **kwargs):
        """
        获取OA中流程配置的流程图xml数据
        需要高权限级别的OA账号, 测试账号 A0009527
        """
        # TODO 对request.user的权限判断
        workflow = OaWorkflowApi()
        oa_user = OaUserInfo.objects.get(
            staff_code_id=settings.OA_WORKFLOW_MANAGER_CODE
        )
        workflow.register_user(oa_user.user_id)
        get_xml_path = "/api/workflow/layout/getXml"
        post_data = {
            "workflowId": wf_id,
            "backstageReadOnly": True,
        }
        res = workflow._post_oa(get_xml_path, post_data=post_data)

        # xml中的节点名value的值需要base64解码
        b64_node_names = re.findall(
            r"value=\"base64_(?P<b64_node_name>\S+)\"", res["xml"]
        )
        b64_node_names = set(b64_node_names)
        for i in b64_node_names:
            node_name = base64.b64decode(i).decode()
            replace_str = f"base64_{i}"
            res["xml"] = res["xml"].replace(replace_str, node_name)
        return Response(res)

    @action(
        detail=False,
        methods=["POST"],
        url_path="oa-callback",
        permission_classes=(),
        authentication_classes=(),
    )
    def oa_callback(self, request, *args, **kwargs):
        """
        OA流程归档回调接口
        """
        data = request.data
        oa_request_id = data["request_id"]
        sign = request.headers.get("Apisign", "")
        if sign != hashlib.md5(str(oa_request_id).encode()).hexdigest().upper():  # noqa: S324
            raise APIException("ApiSign错误")
        if TERMINATE_COLUMN in data:
            status = not int(data[TERMINATE_COLUMN] or 0)
        else:
            status = data["status"]

        # SRM审批记录表事务
        # OA数据库SRM拓展表事务
        approval = get_object_or_404(self.queryset, workflow_request_id=oa_request_id)
        with atomic(using="oa"), atomic():
            if status:
                approval.content_object.approve()
                approval_status = ApprovalStatus.APPROVED
            else:
                approval.content_object.reject()
                approval_status = ApprovalStatus.REJECTED
            approval.approval_status = approval_status
            approval.archive()

            oa_extend = get_object_or_404(
                WorkflowRequestWccExtendInfo.objects.all(),
                REQUESTID_id=int(oa_request_id),
            )
            oa_extend.APPROVAL_STATUS = approval_status
            oa_extend.DOC_STATUS = approval.content_object.status
            oa_extend.save()

        return Response()

    @action(detail=True, url_path="custom-info")
    def custom_info(self, request, *args, **kwargs):
        """
        获取流程部分自定义信息
        """
        instance = self.get_object()
        nodes = RegisterWorkflowNode.objects.filter(
            register_workflow=instance.workflow
        ).order_by("status", "-is_start", "is_end", "node_order")
        node_serializers = RegisterWorkflowNodeSerializer(nodes, many=True)

        # 当前流程所相关的用户
        try:
            oa_user_id = request.user.oa_user_id
        except APIException:
            oa_user_id = -9999999
        related = False
        workflow_requestlog = WorkflowRequestLog.objects.filter(
            REQUESTID_id=int(instance.workflow_request_id)
        )
        for wf_log in workflow_requestlog:
            if oa_user_id == wf_log.OPERATOR_id:
                related = True
                break

            log_to_user_ids = wf_log.RECEIVEDPERSONIDS or ""
            log_to_user_ids = [
                int(i) for i in log_to_user_ids.replace(" ", "").split(",") if i
            ]
            if oa_user_id == log_to_user_ids:
                related = True
                break

        return Response({"nodes": node_serializers.data, "related": related})
