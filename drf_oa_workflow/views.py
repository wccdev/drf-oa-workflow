import datetime

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .mixin import OaWFApiViewMixin


class OaWorkFlowView(OaWFApiViewMixin, APIView):
    @action(detail=False)
    def create_list(self, request, *args, **kwargs):
        """
        可创建流程列表
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        workflow = request.oa_wf_api
        result = workflow.get_create_list()
        _demo = {  # noqa
            "formId": "-269",
            "workflowId": "52021",
            "workflowName": "SRM V0.1",
            "workflowTypeId": "1",
            "workflowTypeName": "系统默认工作流",
        }
        return Response(result)

    @action(detail=False, url_path="todo-list")
    def todo_list(self, request, *args, **kwargs):
        """
        待办列表
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        workflow = request.oa_wf_api
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))
        workflow_id = "???"
        data, page, todo_count = workflow.get_todo_list(workflow_id, page, page_size)
        res = {
            "total": todo_count,
            "page_size": page_size,
            "current_page": page,
            "results": data,
            "userinfo": workflow.user,
        }
        return Response(res)

    @action(detail=False, url_path="handled-list")
    def handled_list(self, request, *args, **kwargs):
        """
        已办列表
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        workflow = request.oa_wf_api
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))
        workflow_id = "???"
        data, page, todo_count = workflow.get_handled_list(workflow_id, page, page_size)
        res = {
            "total": todo_count,
            "page_size": page_size,
            "current_page": page,
            "results": data,
        }
        return Response(res)

    # @action(detail=False, methods=["POST"])
    # def submit(self, request, *args, **kwargs):
    #     data = request.data
    #     _ = demo = {
    #         'requestName': 'Srm-0.1-TEst-001',
    #         'djbh': 'Test-leslie_chan-001', 'cglb': '0', 'cgxlb': '1', 'cjjshj': '12', 'bz': '3'
    #     }
    #     workflow = request.oa_wf_api
    #     workflow_id = "52021"
    #     workflow.register_user(request.user.gc_oa_id)
    #     oa_user = workflow.user
    #     data["sqr"] = request.user.gc_oa_id
    #     data["bm"] = oa_user["deptid"]
    #
    #     title = data.pop("requestName")
    #     remark = data.pop("remark", "")
    #
    #     post_data = {
    #         "mainData": json.dumps([
    #             # {"fieldName": "djbh", "fieldValue": self.date},
    #             {"fieldName": k, "fieldValue": v} for k, v in data.items()
    #         ]),
    #         "otherParams": {},
    #         "remark": remark,
    #         "requestLevel": "0",
    #         "requestName": title,
    #         "workflowId": workflow_id  # 内部价2
    #     }
    #     res = workflow.submit(post_data)
    #     return Response({"oa_request_id": res})

    @action(detail=True, methods=["POST"])
    def review(self, request, oa_request_id, *args, **kwargs):
        """
        审核
        """
        data = request.data
        workflow = request.oa_wf_api
        workflow.register_user(request.user.gc_oa_id)

        # data["sqr"] = request.user.gc_oa_id
        # data["bm"] = oa_user["deptid"]
        remark = data.pop("remark", "")
        main_data = [{"fieldName": k, "fieldValue": v} for k, v in data.items()]  # noqa
        extras = {}
        # if main_data:
        #     doc.purchase_cat = data["cglb"]
        #     doc.purchase_cat2 = data["cgxlb"]
        #     doc.price = str(data["cjjshj"])
        #     doc.currency = data["bz"]
        #     extras = {"mainData": json.dumps(main_data)}
        res = workflow.review(oa_request_id, remark=remark, extras=extras)
        return Response(res)

    @action(detail=True, methods=["POST"])
    def reject(self, request, oa_request_id, *args, **kwargs):
        """
        退回:
        :return:
        """
        data = request.data
        workflow = request.oa_wf_api
        # "324351"
        res = workflow.reject(oa_request_id, node_id=data.get("node_id", ""), remark=data.get("remark", ""))
        return Response(res)

    @action(detail=True, url_path="oa-remarks")
    def oa_remarks(self, request, oa_request_id, *args, **kwargs):
        """
        操作记录
        """
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))
        workflow = request.oa_wf_api
        logs = workflow.get_remark(oa_request_id, page=page, page_size=page_size)

        log_type = {
            "0": "批准",
            "2": "提交",
            "3": "退回",
            "7": "转发",
            "9": "批注",
            "h": "转办",
            "i": "流程干预",
        }
        user_map = request.user.oa_user_map
        for i in logs["data"]:
            i["operateType"] = log_type.get(i["logtype"], "(未知操作，需要定义)")
            i["operatorName"] = user_map[i["operator"]]["name"]
        res = {
            "total": 100,
            "page_size": page_size,
            "current_page": page,
            "results": logs["data"],
        }
        return Response(res)

    @action(detail=True, url_path="oa-info")
    def oa_info(self, request, oa_request_id, *args, **kwargs):
        workflow = request.oa_wf_api
        res = workflow.get_info(oa_request_id)
        return Response(res)

    @action(detail=True, methods=["POST"])
    def transmit(self, request, oa_request_id, *args, **kwargs):
        """
        转发/转办
        :return:
        """
        data = request.data
        workflow = request.oa_wf_api
        res = workflow.transmit(oa_request_id, data["trans_type"], data["user_id"], remark=data["remark"])
        return Response(res)

    @action(detail=True, methods=["POST"])
    def recover(self, request, oa_request_id, *args, **kwargs):
        workflow = request.oa_wf_api
        res = workflow.recover(oa_request_id)
        return Response(res)

    @action(detail=True, url_path="OperatorInfo")
    def operator_info(self, request, oa_request_id, *args, **kwargs):
        workflow = request.oa_wf_api
        res = workflow.get_operator_info(oa_request_id)
        time_format = "%Y-%m-%d %H:%M:%S"
        for i in res["data"]:
            if i["operatetime"]:
                operate_time = datetime.datetime.strptime(f"{i['operatedate']} {i['operatetime']}", time_format)
                receive_time = datetime.datetime.strptime(f"{i['receivedate']} {i['receivetime']}", time_format)
                handle_time = operate_time - receive_time
                handle_days = handle_time.days
                handle_minutes, handle_seconds = divmod(handle_time.seconds, 60)
                handle_hours, handle_minutes = divmod(handle_minutes, 60)
                # print(handle_days, handle_hours, handle_minutes, handle_seconds)
                time_str = ""
                if handle_days:
                    time_str += f"{handle_days}天"
                if handle_hours:
                    time_str += f"{handle_hours}小时"
                if handle_minutes:
                    time_str += f"{handle_minutes}分"
                if handle_seconds:
                    time_str += f"{handle_seconds}秒"
                i["handle_time"] = time_str
            else:
                i["handle_time"] = ""
        return Response(res["data"])

    @action(detail=True)
    def chart(self, request, oa_request_id, *args, **kwargs):
        workflow = request.oa_wf_api
        res = workflow.get_chart_url(oa_request_id)
        return Response(res["data"])

    @action(detail=True)
    def resources(self, request, oa_request_id, *args, **kwargs):
        """
        OA流程明细页 相关资源 数据
        相关流程/相关文档/相关资源
        :param request:
        :param oa_request_id:
        :param args:
        :param kwargs:
        :return:
        """
        workflow = request.oa_wf_api
        res = workflow.get_resources(oa_request_id)
        return Response(res["data"])
