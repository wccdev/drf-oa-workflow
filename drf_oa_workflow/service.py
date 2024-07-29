from __future__ import annotations

import datetime
import random
from itertools import groupby
from string import ascii_letters
from string import digits

from django.contrib.auth import get_user_model
from django.db.models import F

from drf_oa_workflow.choices import ApprovalStatus
from drf_oa_workflow.choices import OAFlowNodeType
from drf_oa_workflow.choices import OAWorkflowLogTypes
from drf_oa_workflow.choices import StatusChoice
from drf_oa_workflow.choices import WFOperationTypes
from drf_oa_workflow.contains import DEFAULT_MAIN_DATA
from drf_oa_workflow.models import WorkflowCurrentOperator
from drf_oa_workflow.models import WorkflowFlowNode
from drf_oa_workflow.models import WorkflowRequestBase
from drf_oa_workflow.models import WorkflowRequestLog
from drf_oa_workflow.utils import OaWorkflowApi

from .settings import api_settings

User = get_user_model()


class WFService:
    from drf_oa_workflow.models import OAWorkflow
    from drf_oa_workflow.models import WorkflowApproval

    @classmethod
    def generate_code(cls, prefix: str, suffix_len: int = 6):
        """
        生成流程编号
        :param prefix: 编号前缀
        :param suffix_len: 编号后缀长度
        """
        time_part = datetime.datetime.today().strftime("%Y%m%d%H%M%S")  # noqa: DTZ002

        salt_str = ascii_letters + digits
        random_suffix = ""
        for _ in range(suffix_len):
            random_salt_index = random.randint(0, len(salt_str) - 1)  # noqa: S311
            random_suffix += salt_str[random_salt_index]

        return f"{prefix}.{time_part}.{random_suffix}"

    @classmethod
    def submit_oa(  # noqa: PLR0913
        cls,
        content_object,
        wf_class: OAWorkflow,
        action,
        title,
        front_form_info,
        main_data: dict | None = None,
        detail_data: list | None = None,
        remark="",
        submitter=None,
    ) -> WorkflowApproval:
        """
        提交流程到OA
        :param content_object:     提交的单据
        :param action:             提交的流程Action类型, srm.core.choices.WorkflowAction
        :param wf_class:  流程(content_object绑定或者对应的OAWorkflow实例)
        :param title:              标题
        :param front_form_info:    前端表单信息
        :param main_data:          流程主表数据
        :param detail_data:        流程子表数据
        :param remark:             备注、批注
        :param submitter:          流程提交人
        """
        # from drf_oa_workflow.models import OAWorkflow
        from drf_oa_workflow.models import WorkflowApproval
        from drf_oa_workflow.models import WorkflowRequestWccExtendInfo

        # 提交的主表数据处理
        main_data = main_data or {}
        main_data.update(DEFAULT_MAIN_DATA)

        # 提交人
        submitter = submitter or content_object.updated_by

        # 流程配置开启
        if wf_class.status == StatusChoice.VALID:
            # 提交到OA
            wf_service = OaWorkflowApi()
            wf_service.register_user(submitter.oa_user_id)

            handled_data = [
                {"fieldName": oa_field, "fieldValue": field_value}
                for oa_field, field_value in main_data.items()
            ]

            # OA流程REQUEST ID
            oa_request_id = wf_service.submit_new(
                wf_class.workflow_id,
                handled_data,
                detail_data=detail_data,
                title=title,
                remark=remark,
            )
            submit_type = WFOperationTypes.SUBMIT
        # 流程配置未开启使用
        else:
            oa_request_id = "0"
            submit_type = WFOperationTypes.SUBMIT_WITHOUT_WF
            content_object.approve()

        approval = WorkflowApproval(
            action=action,
            title=title,
            workflow=wf_class,
            workflow_request_id=oa_request_id,
            content_object=content_object,
            created_by=submitter,
            updated_by=submitter,
            front_form_info=front_form_info,
        )
        # 获取OA流程编号
        approval.get_oa_request_code()
        approval.save()

        # 记录提交
        oa_node_id = 0  # FIXME 需要确认获取到流程的起始节点
        approval.record_operation(submitter, oa_node_id, submit_type, remark=remark)

        # 增加OA扩展表记录
        if oa_request_id != "0":
            WorkflowRequestWccExtendInfo.objects.create(
                REQUESTID_id=int(oa_request_id),
                APPROVAL_STATUS=ApprovalStatus.PENDING,
                DOC_STATUS=content_object.status,
                SOURCE=api_settings.SYSTEM_IDENTIFIER,
            )
        return approval

    @classmethod
    def get_workflow_info_map(cls, oa_request_ids: list):
        """
        批量获取提交到OA的流程在本系统的提交记录以及流程配置信息
        :param oa_request_ids: OA流程requestId[]
        """
        from drf_oa_workflow.models import WorkflowApproval
        from drf_oa_workflow.serializers.workflow_approval import (
            WFListApprovalSerializer,
        )

        approvals = WorkflowApproval.objects.filter(
            workflow_request_id__in=oa_request_ids
        )
        approvals = WFListApprovalSerializer.process_queryset(None, approvals)
        prepare_datas = WFListApprovalSerializer(approvals, many=True).data

        prepare_datas_map = {}
        for i in prepare_datas:
            prepare_datas_map[i["oa_request_id"]] = i
        return prepare_datas_map

    @classmethod
    def get_oa_wf_passed_nodes(cls, oa_request_id):
        """
        从OA获取流程请求日志，主要是节点流水信息
        """

        return list(
            WorkflowRequestLog.objects.exclude(LOGTYPE=OAWorkflowLogTypes.REJECT.value)
            .filter(REQUESTID_id=oa_request_id)
            .values_list("NODEID_id", flat=True)
            .order_by("-OPERATEDATE", "-OPERATETIME")
        )

    @classmethod
    def get_oa_workflow_form_buttons(
        cls, oa_api_server: OaWorkflowApi, approval: WorkflowApproval, oa_node_id
    ):
        """
        从OA获取当前用户当前流程的可操作的按钮组
        :param oa_api_server:
        :param approval: 流程审批记录
        :param oa_node_id: OA流程所处节点ID
        """
        # 1.获取OA流程的菜单按钮
        right_menu_data = oa_api_server.get_operate_buttons(
            approval.workflow_request_id
        )

        # 2.本系统可用按钮
        stand_buttons = [  # noqa: F841
            {
                "menuName": "批注",
                "systemMenuType": "POSTIL_FORWARD",
                "type": "BTN_SUBMIT",
            },
            {"menuName": "提交", "systemMenuType": "SUBMIT", "type": "BTN_SUBMIT"},
            {"menuName": "批准", "systemMenuType": "APPROVE", "type": "BTN_SUBMIT"},
            {"menuName": "退回", "systemMenuType": "REJECT", "type": "BTN_REJECTNAME"},
            {"menuName": "转发", "systemMenuType": "FORWARD", "type": "BTN_FORWARD"},
            {"menuName": "转办", "systemMenuType": "TURN_TO", "type": "BTN_TURNTODO"},
            {"menuName": "传阅", "systemMenuType": "CHUANYUE", "type": "BTN_CHUANYUE"},
            {
                "menuName": "意见征询",
                "systemMenuType": "REMARKADVICE",
                "type": "BTN_REMARKADVICE",
            },
            {
                "menuName": "撤回",
                "systemMenuType": "WF_WITHDRAW",
                "type": "BTN_WIDTHDRAW",
            },
            {"menuName": "删除", "systemMenuType": "DODELETE", "type": "BTN_DODELETE"},
            {
                "menuName": "强制收回",
                "systemMenuType": "BTN_DODRAWBACK",
                "type": "BTN_DORETRACT",
            },
            # {"menuName": "删除", "systemMenuType": "DODELETE", "type": "BTN_DODELETE"},  # noqa: E501
            # {"menuName": "保存", "systemMenuType": "SAVE", "type": "BTN_WFSAVE"},
            # {"menuName": "打印", "systemMenuType": "PRINT", "type": "BTN_PRINT"},
            # {"menuName": "打印日志", "systemMenuType": "PRINT_LOG", "type": "BTN_COLLECT"}  # noqa: E501
        ]
        handled_buttons = {
            "delete": False,  # 删除
            "re_submit": False,  # 重新提交
            "review": False,  # 批准
            "return": False,  # 退回
            "transfer": False,  # 转办
            "forward": False,  # 转发
            "endorse": False,  # 批注
            "withdraw": False,  # 撤回
            "terminate": False,  # 终止
            "do_draw_back": False,  # 强制收回
        }
        oa_buttons = right_menu_data.get("rightMenus", [])
        try:
            oa_wf_node = WorkflowFlowNode.objects.select_related("NODEID").get(
                WORKFLOWID_id=approval.workflow.workflow_id, NODEID_id=oa_node_id
            )
        except WorkflowFlowNode.DoesNotExist:
            oa_wf_node = None
        for button in oa_buttons:
            if button["systemMenuType"] == "SUBMIT":
                # 当前节点不为创建节点, 节点类型为提交，则当做审核节点处理
                if (
                    oa_wf_node
                    and oa_wf_node.NODEID.ISSTART != "1"
                    and OAFlowNodeType.SUBMIT.value == oa_wf_node.NODETYPE
                ):
                    handled_buttons["review"] = True
                else:
                    handled_buttons["re_submit"] = True
            elif button["systemMenuType"] == "APPROVE":
                handled_buttons["review"] = True
                # handled_buttons["terminate"] = True
            elif button["systemMenuType"] == "REJECT":
                handled_buttons["return"] = True
            elif button["systemMenuType"] == "FORWARD":
                handled_buttons["forward"] = True
            elif button["systemMenuType"] == "TURN_TO":
                handled_buttons["transfer"] = True
            elif button["systemMenuType"] == "WF_WITHDRAW":
                handled_buttons["withdraw"] = True
            elif button["systemMenuType"] == "POSTIL_FORWARD":
                handled_buttons["endorse"] = True
            elif button["systemMenuType"] == "BTN_DODRAWBACK":
                handled_buttons["do_draw_back"] = True
            elif button["systemMenuType"] == "DODELETE":
                handled_buttons["delete"] = True

        # 流程终止功能是否可用在本系统判断流程是否有终止节点以及连线
        # FIXME 流程终止归档判断, 需要固定终止归档节点的名称
        if handled_buttons["review"]:
            can_terminate = False
            for edge in approval.workflow.flow_node_relations.all():
                if edge.from_node_id != oa_node_id:
                    continue
                if edge.to_node_name not in ["终止归档", "作废归档"]:
                    continue
                if edge.to_node.is_end != "1":
                    continue
                can_terminate = True
                break
            handled_buttons["terminate"] = can_terminate

        return handled_buttons, oa_buttons

    @classmethod
    def get_oa_workflow_info(cls, approval: WorkflowApproval, current_user: User):
        """
        从OA获取流程的详情
        :param approval: 系统提交到OA的流程记录
        :param current_user: 获取当前流程信息的用户
        """
        # 获取OA中的流程信息
        workflow = OaWorkflowApi()
        workflow.register_user(current_user.oa_user_id)

        # OA中的流程用户
        oa_user = workflow.user
        oa_user_name = oa_user["username"]

        # OA流程操作记录
        oa_workflow_detail = workflow.get_info(approval.workflow_request_id)["data"]
        # 可提交/可审核 权限
        can_edit = oa_workflow_detail["canEdit"]

        # 获取当前节点(对于当前查看或者操作的用户来说，
        # 不同节点用户获取到的流程的当前节点并不相同)
        current_node_id = int(oa_workflow_detail["currentNodeId"])

        # 流程操作按钮权限
        option_buttons, oa_buttons = cls.get_oa_workflow_form_buttons(
            workflow, approval, current_node_id
        )

        handled_detail = {
            # 当前节点（针对当前查看的用户来说）
            "current_node_id": current_node_id,
            # 相关用户信息
            "oa_user_name": oa_user_name,
            "oa_dept_name": oa_user["deptname"],
            # 操作按钮信息(根据流OA程配置一个按钮会对应多个按钮)
            "oa_buttons": oa_buttons,
            "buttons": option_buttons,
        }
        return can_edit, current_node_id, handled_detail

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

    @classmethod
    def get_workflow_info_common(cls, request_ids: list):
        """
        获取指定流程requestIds的当前节点和未操作信息
        """

        request_ids = [int(i) for i in request_ids]
        result = (
            WorkflowRequestBase.objects.filter(REQUESTID__in=request_ids)
            .annotate(requestId=F("REQUESTID"))
            .annotate(current_node_id=F("CURRENTNODEID_id"))
            .annotate(current_node_name=F("CURRENTNODEID__NODENAME"))
            .values("requestId", "current_node_id", "current_node_name")
        )
        return cls.match_un_operators(result)

    @classmethod
    def can_return_oa_nodes(cls, approval, current_node_id, passed_node_ids):
        """
        处理节点,根据当前节点判断已经走过的节点, 标记可退回节点
        :param approval:
        :param current_node_id: 当前节点
        :param passed_node_ids: 已经过节点
        """
        if not current_node_id or not passed_node_ids:
            return []

        # 流程每个节点的前置节点信息
        pre_nodes_map = {}
        for r in approval.workflow.flow_node_relations.all():
            pre_nodes_map.setdefault(r.to_node_id, [])
            pre_nodes_map[r.to_node_id].append(r.from_node_id)

        def get_passed_nodes(node_id):
            nodes = []
            # 当前节点的前置节点
            pre_nodes = pre_nodes_map.get(node_id)
            if not pre_nodes:
                return nodes

            # 当前节点的前置节点中已经在流程中通过的节点
            passed_pre_nodes = [_ for _ in pre_nodes if _ in passed_node_ids]
            if not passed_pre_nodes:
                return nodes

            # 根据已经通过的节点的先后顺序
            # 确定当前节点的的前置节点中
            # 最后经过的是哪个前置节点
            passed_pre_nodes_index_list = [
                passed_node_ids.index(_) for _ in passed_pre_nodes
            ]
            passed_pre_node = passed_node_ids[min(passed_pre_nodes_index_list)]

            nodes.append(passed_pre_node)
            nodes.extend(get_passed_nodes(passed_pre_node))
            return nodes

        return get_passed_nodes(current_node_id)
