import base64
import json
import re
from io import BytesIO
from itertools import groupby

import requests as system_requests
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
from django.apps import apps as django_apps
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from requests.exceptions import JSONDecodeError
from rest_framework.exceptions import APIException

from .db_connections import get_oa_oracle_connection
from .settings import DEFAULT_SYNC_OA_USER_MODEL, SETTING_PREFIX, api_settings

requests: system_requests = api_settings.REQUESTS_LIBRARY


def get_sync_oa_user_model():
    sync_oa_user_model = getattr(settings, "SYNC_OA_USER_MODEL", DEFAULT_SYNC_OA_USER_MODEL)
    try:
        return django_apps.get_model(sync_oa_user_model, require_ready=False)
    except ValueError:
        raise ImproperlyConfigured("SYNC_OA_USER_MODEL must be of the form 'app_label.model_name'")
    except LookupError:
        raise ImproperlyConfigured(
            "SYNC_OA_USER_MODEL refers to model '%s' that has not been installed" % sync_oa_user_model
        )


class FetchOaDbHandler:
    @classmethod
    def pre_checking(cls):
        if not all(
            [
                api_settings.OA_DB_USER,
                api_settings.OA_DB_PASSWORD,
                api_settings.OA_DB_HOST,
                api_settings.OA_DB_PORT,
                api_settings.OA_DB_SERVER_NAME,
            ]
        ):
            raise APIException("未有OA数据库连接配置")

    @classmethod
    def get_oa_user_id_by_work_code(cls, job_code: str) -> tuple:
        """
        通过长工号获取对应的OA用户id
        :param job_code: 长工号， A0009527...
        :return: OA用户ID, OA用户部门ID
        """
        cls.pre_checking()
        sql = f"""
            SELECT {api_settings.OA_DB_USER_FETCH_COLUMNS}
            FROM {api_settings.OA_DB_USER_TABLE}
            WHERE {api_settings.OA_DB_USER_STAFF_CODE_COLUMN} = '{job_code}'
            """
        with get_oa_oracle_connection().cursor() as cursor:
            cursor.execute(sql)
            res = cursor.fetchone()
        if not res:
            return None, None
        return res[0], res[1]

    @classmethod
    def get_oa_users_id_by_work_code(cls, job_codes: list) -> list:
        """
        批量通过长工号获取对应的OA用户id
        :param job_codes: 长工号， ["A0009527", "A0009528", ...]
        :return: [[OA用户ID, OA用户部门ID], ...] -> [[18781, 23], [18782, 23], ...]
        """
        cls.pre_checking()
        job_codes = [f"'{i}'" for i in job_codes]
        conditions = f"({','.join(job_codes)})"
        sql = f"""
            SELECT {api_settings.OA_DB_USER_FETCH_COLUMNS}
            FROM {api_settings.OA_DB_USER_TABLE}
            WHERE {api_settings.OA_DB_USER_STAFF_CODE_COLUMN} IN {conditions}
            """
        with get_oa_oracle_connection().cursor() as cursor:
            cursor.execute(sql)
            res = cursor.fetchall()
        return list(res)

    @classmethod
    def get_all_oa_users(cls, fields=None, capital=True) -> list:
        """
        获取全部OA用户信息
        :param fields: 查询字段
        :param capital: 字段名大写
        :return:
        """
        cls.pre_checking()
        user_table_alias = "U"
        dept_table_alias = "D"
        default_fields = (
            f"{user_table_alias}.{api_settings.OA_DB_USER_ID_COLUMN},"
            f"{user_table_alias}.{api_settings.OA_DB_USER_STAFF_CODE_COLUMN},"
            f"{user_table_alias}.{api_settings.OA_DB_USER_DEPT_ID_COLUMN},"
            f"{user_table_alias}.{api_settings.OA_DB_USER_NAME_COLUMN},"
            f"{dept_table_alias}.{api_settings.OA_DB_DEPT_NAME_COLUMN}"
        )
        fetch_fields = fields or default_fields
        sql = f"""
        SELECT {fetch_fields}
        FROM
            {api_settings.OA_DB_USER_TABLE} {user_table_alias}
        LEFT JOIN {api_settings.OA_DB_USER_DEPT_TABLE} {dept_table_alias}
        ON {user_table_alias}.{api_settings.OA_DB_USER_DEPT_ID_COLUMN} = {dept_table_alias}.{api_settings.OA_DB_DEPT_ID_COLUMN}
        WHERE
            {user_table_alias}.{api_settings.OA_DB_USER_STAFF_CODE_COLUMN} IS NOT NULL
        """  # noqa
        with get_oa_oracle_connection().cursor() as cursor:
            cursor.execute(sql)
            columns = [col[0].upper() if capital else col[0].lower() for col in cursor.description]
            cursor.rowfactory = lambda *values: dict(zip(columns, values))
            res = cursor.fetchall()
        return list(res)


class OaApi(FetchOaDbHandler):
    TOKEN_KEY = "token"
    CACHE_TOKEN_KEY = "oa-api-token"
    REQUEST_CONTENTTYPE = "application/x-www-form-urlencoded; charset=utf-8"
    REQUEST_HEADERS = {"Content-Type": REQUEST_CONTENTTYPE}

    PUBLIC_KEY_PREFIX = "-----BEGIN PUBLIC KEY-----"
    PUBLIC_KEY_SUFFIX = "-----END PUBLIC KEY-----"

    @classmethod
    def handle_pub_key(cls, pub_key):
        """
        处理公钥格式
        :param pub_key:
        :return:
        """
        start = f"{cls.PUBLIC_KEY_PREFIX}\n"
        end = cls.PUBLIC_KEY_SUFFIX
        result = ''
        # 分割key，每64位长度换一行
        length = len(pub_key)
        divide = 64  # 切片长度
        offset = 0  # 拼接长度
        while length - offset > 0:
            if length - offset > divide:
                result += pub_key[offset : offset + divide] + '\n'
            else:
                result += pub_key[offset:] + '\n'
            offset += divide
        result = start + result + end
        return result

    def __init__(self):
        self.oa_host = api_settings.OA_HOST
        self.app_id = api_settings.APP_ID
        if not api_settings.APP_SPK.startswith(self.PUBLIC_KEY_PREFIX):
            self.app_spk = self.handle_pub_key(api_settings.APP_SPK)
        else:
            self.app_spk = api_settings.APP_SPK
        self.app_encrypted_secret = self.__encrypt_with_spk(api_settings.APP_RAW_SECRET)
        # self.encrypt_userid = self.__get_encrypt_userid(oa_user_id)
        self.encrypt_userid = ""

        self.token = cache.get(self.CACHE_TOKEN_KEY)

        self.maximum_recursion = 8
        self.recursion_c = 0

    def __helpme(self, error):
        if self.recursion_c >= self.maximum_recursion:
            raise ValueError(error)
        self.recursion_c += 1

    def get_sso_token(self, staff_code):
        """
        获取SSO TOKEN
        :param staff_code: 用户工号或者为oa的登入名, A0009527
        """
        if not api_settings.OA_SSO_TOKEN_APP_ID:
            raise ValueError(f"使用此方法请先配置f'{SETTING_PREFIX}'.'OA_SSO_TOKEN_APP_ID'")
        api_path = "/ssologin/getToken"
        headers = {"Content-Type": self.REQUEST_CONTENTTYPE}
        post_data = {"appid": api_settings.OA_SSO_TOKEN_APP_ID, "loginid": staff_code}
        token = self._post_oa(api_path, post_data=post_data, headers=headers, need_json=False)
        # RIGHT DCA2CD1A9AFA13A8CEA5C82A5CDE8D7ADABA81522626723EC559D733649FABDC
        # ERROR Token获取失败: 认证应用未注册
        if "失败" in token:
            raise APIException(token)
        return token

    @property
    def user(self) -> dict:
        if getattr(self, "_user", None):
            return self._user
        return {"userid": "", "deptid": None, "deptname": ""}

    def register_user(self, oa_user_id: str):
        oa_user_id = str(oa_user_id)
        if getattr(self, "user", {}) and str(self.user["userid"]) == oa_user_id:
            return

        if not self.token:
            self.get_token()
        self.oa_user_id = oa_user_id
        self.encrypt_userid = self.__encrypt_with_spk(oa_user_id)
        self._user = self.userinfo()

    def register_user_with_job_code(self, job_code: str):
        """
        使用工号
        :param job_code: 长工号， A0009527...
        """
        oa_user_id, oa_user_dept_id = self.get_oa_user_id_by_work_code(job_code)
        if not oa_user_id:
            raise APIException(f"Oa中未查询到工号为'{job_code}'的账号")
        self.register_user(oa_user_id)

    def __encrypt_with_spk(self, text: str):
        """
        使用OA SPK加密文本
        :param text:
        :return:
        """
        publickey = RSA.import_key(self.app_spk.encode())
        pk = PKCS1_v1_5.new(publickey)
        encrypt_text = pk.encrypt(text.encode())
        result = base64.b64encode(encrypt_text)
        return result.decode()

    def get_token(self, expr=10800):
        """
        获取Oa API Token
        :param expr:
        :return:
        """
        api_path = "/api/ec/dev/auth/applytoken"
        headers = {
            "appid": self.app_id,
            "secret": self.app_encrypted_secret,
            "time": str(expr),
        }
        res = self._post_oa(api_path, headers=headers)
        # resp.text {
        # "msg":"获取成功!","code":0,"msgShowType":"none","status":true,"token":"e3d7e45b-805c-43c3-9c0c-e452135ae1ea"
        # }
        print("新Token: ", res[self.TOKEN_KEY])
        self.token = res[self.TOKEN_KEY]
        cache.set(self.CACHE_TOKEN_KEY, self.token, timeout=None)
        return self.token

    @property
    def _request_headers(self):
        if not self.encrypt_userid:
            raise NotImplementedError("调用前请先使用.register_user(OA_USER_ID: str)方法注册当前要操作的OA账号")
        headers = {
            "Content-Type": self.REQUEST_CONTENTTYPE,
            "appid": self.app_id,
            self.TOKEN_KEY: self.token,
            "userid": self.encrypt_userid,
        }
        return headers

    def __request(
        self,
        api_path,
        rf: any([system_requests.get, system_requests.post]),
        headers: dict = None,
        need_json=True,
        **kwargs,  # noqa
    ):
        url = f"{self.oa_host}{api_path}"
        headers = headers or self._request_headers
        resp: system_requests.Response = rf(url, headers=headers, **kwargs)

        if resp.status_code != 200:
            # 错误导致递归的问题
            # print(resp.text)
            # raise SystemError(f"OA: Response[{resp.status_code}]")
            self.__helpme(f"OA: Response[{resp.status_code}]")
            headers[self.TOKEN_KEY] = self.get_token()
            return self.__request(api_path, rf, headers=headers, need_json=need_json, **kwargs)

        if not need_json:
            return resp.text

        try:
            res = resp.json()
        except JSONDecodeError:
            raise ValueError(f"OA: {resp.text}")
            res = {"code": -1}

        # TODO 错误响应
        # {"msg":"secret解密失败,请检查加密内容.","code":-1,"msgShowType":"none","status":false}
        # {'msg':'token不存在或者超时：4225b79b-9407-47ca-82ab-d66850c4ec3e','code':-1,'msgShowType':'none','status':False}
        # {'msg': '登录信息超时', 'errorCode': '002', 'status': False}
        # {"msg":"该账号存在异常,单点登录失败","code":-1,"msgShowType":"none","status":false}
        if type(res) is dict and not res.get("status", True):
            resp_msg = res.get("msg", "")
            if res.get("code") == -1:
                if resp_msg == "secret解密失败,请检查加密内容.":
                    explain_suf = "(或为OA APP_SPK失效)"
                elif resp_msg.startswith("认证信息错误"):
                    explain_suf = "(或为OA APP_SECRET失效)"
                elif resp_msg.startswith("token不存在或者超时"):
                    self.__helpme(resp.text)
                    headers[self.TOKEN_KEY] = self.get_token()
                    return self.__request(api_path, rf, headers=headers, need_json=need_json, **kwargs)
                else:
                    explain_suf = "(或为OA License过期)"
                raise APIException(detail=f"OA Error: {resp_msg}。{explain_suf}")
            if resp_msg == "登录信息超时":
                self.__helpme(resp.text)
                headers[self.TOKEN_KEY] = self.get_token()
                return self.__request(api_path, rf, headers=headers, need_json=need_json, **kwargs)
            raise ValueError(f"Error: {resp.text}")
        if type(res) is dict and res.get("code", "") and res["code"] != "SUCCESS":
            raise APIException(detail=f"OA提示: {res['code']}, {res.get('errMsg', '')}")
        return res

    def _get_oa(self, api: str, params: dict = None, headers: dict = None, need_json=True):
        res = self.__request(api, requests.get, params=params, headers=headers, need_json=need_json)
        self.recursion_c = 0
        return res

    def _post_oa(self, api: str, post_data: dict = None, headers: dict = None, need_json=True, **kwargs):
        res = self.__request(api, requests.post, data=post_data, headers=headers, need_json=need_json, **kwargs)
        self.recursion_c = 0
        return res

    def _page_data(self, page_count_path, page_data_path, workflow_id, page=1, page_size=10, conditions: dict = None):
        """
        请求分页数据
        :param page_count_path:
        :param page_data_path:
        :param workflow_id:
        :param conditions: 查询条件
            -- archivestatus  流程是否归档。 1: 已归档 2: 未归档
            -- nodetype:      当前节点类型。 0: 创建，1: 批准，2: 提交，3: 归档
            -- requestlevel:  紧急程度      0: 正常 1: 重要 2: 紧急
            -- workflowIds：  流程路径id 以','分隔
            -- workflowTypes：流程类型id 以','分隔
        :return:
        """
        """
        - 测试目录                       workflowTypes    type_id = 1021
           S-返利申请备案流程-测试上线版    workflowIds           id = 49022
           内部价2                       workflowIds           id = 51022
           内部价                        workflowIds           id = 50522
        """
        if not conditions:
            conditions = {}
        search_conditions = {
            "conditions": json.dumps(
                {
                    # "workflowTypes": "1021",  # 流程目录ID  2,3,4
                    **conditions,
                    "workflowIds": workflow_id,  # 流程ID     1,2,3
                }
            )
        }
        resp = self._post_oa(page_count_path, post_data=search_conditions, need_json=False)
        todo_count = int(resp)

        if (page - 1) * page_size >= todo_count:
            return [], page, todo_count

        post_data = {"pageNo": str(page), "pageSize": str(page_size), **search_conditions}
        res: list = self._post_oa(
            page_data_path,
            post_data=post_data,  # , need_json=False
        )

        return res, page, todo_count

    def userinfo(self) -> dict:
        """
        获取账号信息
        :return:
        """
        api_path = "/api/hrm/login/getAccountList"
        user_info = self._get_oa(api_path)
        # user_info = resp.json()
        _ = {
            "data": {
                "accountlist": [
                    {
                        "subcompanyid": 21,
                        "jobs": "Default",
                        "icon": "/messager/images/icon_m_wev8.jpg",
                        "deptid": 21,
                        "subcompanyname": "格科微电子（上海）有限公司",
                        "iscurrent": "1",
                        "userid": "18781",
                        "username": "Leslie Chan",
                        "deptname": "公共关系部",
                    }
                ],
                "subcompanyid": 21,
                "jobs": "Default",
                "icon": "/messager/images/icon_m_wev8.jpg",
                "deptid": 21,
                "subcompanyname": "格科微电子（上海）有限公司",
                "iscurrent": "1",
                "userid": "18781",
                "deptname": "公共关系部",
                "userLanguage": "7",
                "showSearch": False,
                "showMore": True,
                "username": "Leslie Chan",
                "fontSetting": False,
            },
            "status": "1",
        }
        return user_info["data"]

    def upload_file(self, oa_category_id: str, file_source: BytesIO, file_name):
        """
        上传附件
        :param oa_category_id: Oa附件目录ID
        :param file_source: 上传到Oa的文件内容
        :param file_name: 上传到Oa的文件名称
        :return:
        """
        api_path = "/api/doc/upload/uploadFile2Doc"
        # api_path = "/api/doc/upload/uploadFile"
        body = {"category": oa_category_id, "name": file_name}
        headers = self._request_headers.copy()
        headers.pop("Content-Type")
        files = {"file": file_source}
        resp = self._post_oa(api_path, post_data=body, headers=headers, files=files)
        return resp["data"]["fileid"]

    def get_workflow_chart_url(self, staff_code: str, oa_workflow_id):
        """
        获取流程配置的流程图链接， 不需要注册用户
        :param staff_code:     拥有OA可配置流程权限的账号工号
        :param oa_workflow_id: 要获取流程图的OA流程ID
        """
        oa_host = api_settings.OA_HOST
        get_chat_path = (
            "/workflow/workflowDesign/readOnly-index.html"
            "?isFree=0&isAllowNodeFreeFlow=0&isReadOnlyModel=true"
            f"&isFlowModel=0&hasFreeNode=0&showE9Pic=1&isFromWfForm=true&workflowId={oa_workflow_id}"
        )
        oa_sso_token = self.get_sso_token(staff_code)
        oa_chat_url = f"{oa_host}{get_chat_path}&ssoToken={oa_sso_token}"
        return oa_chat_url

    def get_workflow_chart_xml(self, oa_workflow_id):
        """
        获取流程配置的流程图xml数据
        需要高权限级别的OA账号
        :param oa_workflow_id: 要获取流程图的OA流程ID
        """
        get_xml_path = "/api/workflow/layout/getXml"
        post_data = {
            "workflowId": oa_workflow_id,
            "backstageReadOnly": True,
        }
        res = self._post_oa(get_xml_path, post_data=post_data)
        xml_content = res.get("xml", "")
        if not xml_content:
            return ""

        # xml中的节点名value的值需要base64解码
        b64_node_names = re.findall(r"value=\"base64_(?P<b64_node_name>\S+)\"", xml_content)
        b64_node_names = set(b64_node_names)
        for i in b64_node_names:
            node_name = base64.b64decode(i).decode()
            replace_str = f"base64_{i}"
            xml_content = xml_content.replace(replace_str, node_name)
        return xml_content


class OaWorkFlow(OaApi):
    def get_todo_list(self, workflow_id, page, page_size, conditions=None):
        """
        待办流程
        """
        count_api_path = "/api/workflow/paService/getToDoWorkflowRequestCount"
        data_api_path = "/api/workflow/paService/getToDoWorkflowRequestList"
        data, page, total_count = self._page_data(
            count_api_path, data_api_path, workflow_id, page=page, page_size=page_size, conditions=conditions
        )
        # 示例数据 api_example_data.TODO_LIST_DEMO
        return data, page, total_count

    def get_doing_list(self, workflow_id, page, page_size, conditions=None):
        """
        待办列表->待处理
        """
        count_api_path = "/api/workflow/paService/getDoingWorkflowRequestCount"
        data_api_path = "/api/workflow/paService/getDoingWorkflowRequestList"
        data, page, total_count = self._page_data(
            count_api_path, data_api_path, workflow_id, page=page, page_size=page_size, conditions=conditions
        )
        return data, page, total_count

    def get_unread_list(self, workflow_id, page, page_size, conditions=None):
        """
        待办列表->待阅
        """
        count_api_path = "/api/workflow/paService/getToBeReadWorkflowRequestCount"
        data_api_path = "/api/workflow/paService/getToBeReadWorkflowRequestList"
        data, page, total_count = self._page_data(
            count_api_path, data_api_path, workflow_id, page=page, page_size=page_size, conditions=conditions
        )
        return data, page, total_count

    def get_rejected_list(self, workflow_id, page, page_size, conditions=None):
        """
        待办列表->被退回
        """
        count_api_path = "/api/workflow/paService/getBeRejectWorkflowRequestCount"
        data_api_path = "/api/workflow/paService/getBeRejectWorkflowRequestList"
        data, page, total_count = self._page_data(
            count_api_path, data_api_path, workflow_id, page=page, page_size=page_size, conditions=conditions
        )
        return data, page, total_count

    def get_handled_list(self, workflow_id, page, page_size, conditions=None):
        """
        已办流程
        """
        count_api_path = "/api/workflow/paService/getHandledWorkflowRequestCount"
        data_api_path = "/api/workflow/paService/getHandledWorkflowRequestList"
        data, page, total_count = self._page_data(
            count_api_path, data_api_path, workflow_id, page=page, page_size=page_size, conditions=conditions
        )
        # 示例数据 api_example_data.HANDLED_LIST_DEMO
        return data, page, total_count

    def get_create_list(self):
        """
        可创建流程
        """
        # count_api_path = "/api/workflow/paService/getCreateWorkflowCount"
        api_path = "/api/workflow/paService/getCreateWorkflowList"
        post_data = {
            "conditions": json.dumps(
                {
                    # "wfIds": "51022",  # 流程
                    "wfTypeIds": "1"  # "1021"  # 目录
                }
            )
        }
        res: list = self._post_oa(api_path, post_data=post_data)
        # 示例数据 api_example_data.CREATE_LIST_DEMO
        result = []
        res.sort(key=lambda x: x["workflowTypeName"])
        for type_name, g in groupby(res, key=lambda x: x["workflowTypeName"]):
            result.append({"workflowTypeName": type_name, "workflows": list(g)})
        return result

    def submit(self, post_data: dict, work_flow_id: str = None):
        """
        创建流程
        :param post_data:
        :param work_flow_id: Oa中的流程ID
        # :param oa_detail_table: SCM单据ID
        """
        # work_flow_id 51002 创建流程
        # work_flow_id 51003 编辑流程

        # doc_id 单据ID

        # 示例数据 api_example_data.SUBMIT_DATA_DEMO
        api_path = "/api/workflow/paService/doCreateRequest"
        res: dict = self._post_oa(api_path, post_data=post_data)
        oa_request_id = res["data"]["requestid"]
        return oa_request_id

    def submit_new(
        self, work_flow_id, main_data: list, detail_data: list = None, title="", remark="", request_level=""
    ):
        """
        创建流程
        :param work_flow_id: Oa中的流程ID
        :param main_data: 提交流程的主表数据
        :param detail_data: 提交流程的子表数据
        :param title: 提交流程的标题
        :param remark: 提交流程的备注（审批意见）
        :param request_level: 流程紧急度（如果有）
        """
        if not work_flow_id:
            raise APIException("需要提交流程的流程ID")
        if not main_data:
            raise APIException("需要提交流程的主表数据")
        post_data = {
            "mainData": json.dumps(main_data),
            "detailData": json.dumps(detail_data),
            "otherParams": {},
            "remark": remark,
            # "requestLevel": "0",
            # "requestName": "标题",
            "workflowId": str(work_flow_id),
        }
        if title:
            post_data["requestName"] = title
        if request_level:
            post_data["requestLevel"] = request_level

        # 示例数据 api_example_data.SUBMIT_DATA_DEMO
        api_path = "/api/workflow/paService/doCreateRequest"
        res: dict = self._post_oa(api_path, post_data=post_data)
        oa_request_id = res["data"]["requestid"]
        return oa_request_id

    def review(self, request_id: str, remark="", extras: dict = None):
        """
        提交/审核
        :param request_id OA流程请求ID
        :param remark
        :param extras
        """
        api_path = "/api/workflow/paService/submitRequest"
        post_data = {"otherParams": {}, "remark": remark, "requestId": request_id}
        if extras:
            post_data.update(extras)
        resp = self._post_oa(api_path, post_data=post_data)

        # ERROR DATA
        _ERROR = {  # noqa
            "code": "NO_PERMISSION",
            "errMsg": {"isremark": 2},
            "reqFailMsg": {
                "keyParameters": {},
                "msgInfo": {},
                "msgType": "NO_REQUEST_SUBMIT_PERMISSION",
                "otherParams": {},
            },
        }
        return resp

    def reject(self, request_id: str, node_id: str = "", remark=""):
        """
        退回流程
        """
        api_path = "/api/workflow/paService/rejectRequest"
        other_params = "{}"
        if node_id:
            other_params = json.dumps({"RejectToType": 0, "RejectToNodeid": int(node_id)})

        post_data = {"otherParams": other_params, "remark": remark, "requestId": request_id}
        resp = self._post_oa(api_path, post_data=post_data)

        # ERROR DEEMO
        _ERROR = {  # noqa
            "code": "NO_PERMISSION",
            "errMsg": {"isremark": 2, "takisremark": -1, "nodeType": 0},
            "reqFailMsg": {
                "keyParameters": {},
                "msgInfo": {},
                "msgType": "NO_REQUEST_SUBMIT_PERMISSION",
                "otherParams": {},
            },
        }
        _OK = {  # noqa
            "code": "SUCCESS",
            "errMsg": {},
            "reqFailMsg": {"keyParameters": {}, "msgInfo": {}, "otherParams": {"doAutoApprove": "0"}},
        }
        return resp

    def get_chart_url(self, request_id: str, staff_code):
        """
        OA流程明细页 流程图 数据
        :param request_id: OA流程实例ID
        :param staff_code: 用户工号或者为oa的登入名, A0009527
        :return:
        """
        api_path = "/api/workflow/paService/getRequestFlowChart"
        params = {"requestid": request_id}
        # params = None
        resp = self._get_oa(api_path, params=params)
        _ = {  # noqa
            "code": "SUCCESS",
            "data": {
                "chartUrl": """
                /workflow/workflowDesign/readOnly-index.html?requestid=315470
                &f_weaver_belongto_userid=1&f_weaver_belongto_usertype=0
                &isFree=0&isAllowNodeFreeFlow=&isReadOnlyModel=true
                &isFlowModel=0&hasFreeNode=0&showE9Pic=1&isFromWfForm=true&workflowId=50021
                """
            },
            "errMsg": {},
        }
        # 获取单点Token
        sso_token = self.get_sso_token(staff_code)
        resp["data"]["chartUrl"] = resp["data"]["chartUrl"] + f"&ssoToken={sso_token}"
        return resp

    def get_status(self, request_id: str):
        """
        获取流程状态
        :param request_id:
        :return:
        """
        api_path = "/api/workflow/paService/getRequestStatus"
        params = {"requestId": request_id}
        resp = self._get_oa(api_path, params=params)
        # 示例数据 api_example_data.WF_STATUS_DATA_DEMO
        return resp

    def get_operator_info(self, request_id):
        """
        OA流程明细页 流程状态 数据
        :param request_id:
        :return:
        """
        api_path = "/api/workflow/paService/getRequestOperatorInfo"
        res = self._get_oa(api_path, params={"requestId": request_id})
        return res

    def get_resources(self, request_id):
        """
        OA流程明细页 相关资源 数据
        相关流程/相关文档/相关资源
        :param request_id:
        :return:
        """
        api_path = "/api/workflow/paService/getRequestResources"
        params = {"requestId": request_id}
        result = self._get_oa(api_path, params=params)
        # 示例数据 api_example_data.WF_RESOURCE_DATA_DEMO
        # 资源类型 type
        # 1: 相关流程
        # 2: 相关文档
        # 3: 相关附件
        # result = _
        type_map = {1: "相关流程", 2: "相关文档", 3: "相关附件"}
        for res in result["data"]:
            if res["type"] == 3:  # 相关附件
                pass
            res["typeName"] = type_map[res["type"]]
        return result

    def get_remark(self, request_id, page=1, page_size=10):
        """
        流程意见
        :return:
        """
        api_path = "/api/workflow/paService/getRequestLog"
        post_data = {"requestId": request_id, "otherParams": json.dumps({"pageSize": page_size, "pageNumber": page})}
        resp = self._get_oa(api_path, params=post_data)
        # 示例数据 api_example_data.WF_REMARK_DATA_DEMO
        return resp

    def get_info(self, request_id):
        """
        流程信息
        :param request_id:
        :return:
        """
        api_path = "/api/workflow/paService/getWorkflowRequest"
        res = self._get_oa(api_path, params={"requestId": request_id})
        # 示例数据 api_example_data.WF_INFO_DATA_DEMO
        return res

    def transmit(self, request_id, trans_type, user_id: str, remark: str = ""):
        """
        转发、意见征询、转办(对外)
        :param request_id:
        :param trans_type:
        :param user_id:
        :param remark:
        :return:
        """
        api_path = "/api/workflow/paService/forwardRequest"
        if trans_type == 3:
            if len(user_id.split(",")) > 1:
                raise APIException(detail="转办只能转给一个用户")
        post_data = {
            "forwardFlag": trans_type,  # 1:转发  2:意见征询 3:转办
            "forwardResourceIds": user_id,
            "otherParams": {},
            "remark": remark,
            "requestId": request_id,
        }
        resp = self._post_oa(api_path, post_data=post_data)
        return resp

    def recover(self, request_id):
        """
        强制收回
        :param request_id:
        :return:
        """
        api_path = "/api/workflow/paService/doForceDrawBack"
        post_data = {"requestId": request_id}
        resp = self._post_oa(api_path, post_data=post_data)
        _ = {"code": "SUCCESS", "errMsg": {}}  # noqa
        return resp
