import datetime

from django.db import models

from drf_oa_workflow.choices import OAFlowNodeType
from drf_oa_workflow.choices import OAWFCOIsRemarks
from drf_oa_workflow.choices import OAWFCOViewType
from drf_oa_workflow.choices import OAWFHandleReSubmit
from drf_oa_workflow.choices import OAWFHandleReSubmitDefault
from drf_oa_workflow.choices import OAWFOperateCode
from drf_oa_workflow.choices import OAWFOperateType
from drf_oa_workflow.choices import OAWFRejectType
from drf_oa_workflow.choices import OAWorkflowLogTypes
from drf_oa_workflow.db.manager import CurrentOperatorManager
from drf_oa_workflow.db.manager import WorkflowManager
from drf_oa_workflow.db.models import OADbBaseModel

__all__ = [
    "WorkflowBase",
    "WorkflowCurrentOperator",
    "WorkflowFlowNode",
    "WorkflowNodeBase",
    "WorkflowNodeLink",
    "WorkflowRequestBase",
    "WorkflowRequestLog",
    "WorkflowRequestOperateLog",
    "WorkflowType",
]


class WorkflowCurrentOperator(OADbBaseModel):
    """
    OA流程当前请求人
    字段定义查看网址
    https://dougge.top/
    """

    ID = models.IntegerField(primary_key=True)
    REQUESTID = models.ForeignKey(
        "WorkflowRequestBase",
        db_column="REQUESTID",
        to_field="REQUESTID",
        null=True,
        on_delete=models.DO_NOTHING,
        related_name="current_operators",
        verbose_name="流程REQUESTID",
    )
    USERID = models.ForeignKey(
        "drf_oa_workflow.HRMResource",
        db_column="USERID",
        to_field="ID",
        null=True,
        on_delete=models.DO_NOTHING,
        verbose_name="创建人ID",
    )
    USERTYPE = models.IntegerField(
        null=True, verbose_name="用户类型(1、人力资源; 2、客户)"
    )
    VIEWTYPE = models.IntegerField(
        null=True, choices=OAWFCOViewType.choices, verbose_name="查看标志"
    )
    ISREMARK = models.IntegerField(
        null=True, choices=OAWFCOIsRemarks.choices, verbose_name="操作类型"
    )
    ISLASTTIMES = models.IntegerField(null=True)
    ISREJECT = models.CharField(  # noqa: DJ001
        max_length=100, null=True, blank=True, verbose_name="是否为退回前的节点操作人"
    )
    ISBEREJECT = models.CharField(  # noqa: DJ001
        max_length=100, null=True, blank=True, verbose_name="是否退回"
    )
    RECEIVEDATE = models.CharField(  # noqa: DJ001
        max_length=200, null=True, blank=True, verbose_name="接收日期"
    )
    RECEIVETIME = models.CharField(  # noqa: DJ001
        max_length=200, null=True, blank=True, verbose_name="接收时间"
    )
    VIEWDATE = models.CharField(  # noqa: DJ001
        max_length=200, null=True, blank=True, verbose_name="查看日期"
    )
    VIEWTIME = models.CharField(  # noqa: DJ001
        max_length=200, null=True, blank=True, verbose_name="查看时间"
    )
    FIRSTVIEWDATE = models.CharField(  # noqa: DJ001
        max_length=200, null=True, blank=True, verbose_name="初次查看日期"
    )
    FIRSTVIEWTIME = models.CharField(  # noqa: DJ001
        max_length=200, null=True, blank=True, verbose_name="初次查看时间"
    )
    OPERATEDATE = models.CharField(  # noqa: DJ001
        max_length=200, null=True, blank=True, verbose_name="操作日期"
    )
    OPERATETIME = models.CharField(  # noqa: DJ001
        max_length=200, null=True, blank=True, verbose_name="操作时间"
    )
    NODEID = models.IntegerField(null=True)
    AGENTORBYAGENTID = models.IntegerField(null=True)
    AGENTTYPE = models.CharField(max_length=200, null=True, blank=True)  # noqa: DJ001

    objects = CurrentOperatorManager()

    class Meta:
        managed = False
        db_table = 'ECOLOGY"."WORKFLOW_CURRENTOPERATOR'
        verbose_name = verbose_name_plural = "OA流程当前请求人"

    def imitate_oa_view(self, oa_user_id: int):
        """
        模拟OA用户查看流程操作
        :param oa_user_id: 实施查看操作的OA用户id
        """
        if oa_user_id != self.USERID_id:
            return

        now = datetime.datetime.now()  # noqa: DTZ005
        now_date = now.strftime("%Y-%m-%d")
        now_time = now.strftime("%H:%M:%S")
        # 查看类型
        if self.VIEWTYPE != OAWFCOViewType.VIEWED:
            self.VIEWTYPE = OAWFCOViewType.VIEWED
        # 操作时间
        if not self.OPERATEDATE and not self.OPERATETIME:
            self.OPERATEDATE = now_date
            self.OPERATETIME = now_time
        # 初次查看时间
        if not self.FIRSTVIEWDATE and not self.FIRSTVIEWTIME:
            self.FIRSTVIEWDATE = now_date
            self.FIRSTVIEWTIME = now_time
        # 查看时间
        # if not self.VIEWDATE and not self.VIEWTIME:
        self.VIEWDATE = now_date
        self.VIEWTIME = now_time

        self.save()


class WorkflowType(OADbBaseModel):
    ID = models.IntegerField(primary_key=True)
    TYPENAME = models.CharField(verbose_name="目录", max_length=1000)
    TYPEDESC = models.CharField(  # noqa: DJ001
        verbose_name="描述", null=True, blank=True, max_length=1000
    )
    ICONKEY = models.CharField(  # noqa: DJ001
        verbose_name="ICONKEY", null=True, blank=True, max_length=1000
    )
    DSPORDER = models.IntegerField(verbose_name="顺序", null=True, blank=True)
    UUID = models.CharField(verbose_name="UUID", max_length=50)

    class Meta:
        managed = False
        db_table = 'ECOLOGY"."WORKFLOW_TYPE'
        verbose_name = verbose_name_plural = "OA流程目录信息"


class WorkflowBase(OADbBaseModel):
    """
    流程基本信息
    """

    ID = models.IntegerField(primary_key=True)
    WORKFLOWNAME = models.CharField(  # noqa: DJ001
        max_length=300, blank=True, null=True, verbose_name="流程名称"
    )
    FORMID = models.IntegerField(verbose_name="表单ID")
    # WORKFLOWTYPE = models.IntegerField(verbose_name="所属路径ID")
    WORKFLOWTYPE = models.ForeignKey(
        WorkflowType,
        db_column="WORKFLOWTYPE",
        to_field="ID",
        null=True,
        on_delete=models.DO_NOTHING,
        related_name="+",
        verbose_name="流程目录ID",
    )
    ISVALID = models.IntegerField(
        verbose_name="生效信息"
    )  # 0：无效 1：有效 2:测试 3:历史版本
    VERSION = models.IntegerField(verbose_name="版本", null=True)
    ISTEMPLATE = models.CharField(  # noqa: DJ001
        verbose_name="是否为流程模板", max_length=10, null=True
    )  # 0：否 1：是
    TEMPLATEID = models.IntegerField(verbose_name="模板ID", null=True)
    ACTIVEVERSIONID = models.IntegerField(
        verbose_name="当前流程所属活动版本id", null=True
    )
    DSPORDER = models.IntegerField(verbose_name="顺序", null=True)
    WFIDENTKEY = models.IntegerField(verbose_name="流程ID标识", null=True)

    def into_srm_dict(self):
        """
        CASE
            WHEN VERSION IS NULL THEN NULL
            ELSE TEMPLATEID
        END AS parent_id,
        CASE
            WHEN VERSION IS NULL THEN 1
            ELSE VERSION
        END AS work_flow_version
        """
        return {
            "work_flow_id": self.ID,
            "name": self.WORKFLOWNAME,
            "work_flow_type_id": self.WORKFLOWTYPE_id,
            "work_flow_form_id": self.FORMID,
            "is_active_version": self.ISVALID,
            "parent_id": self.TEMPLATEID if self.VERSION else None,
            "work_flow_version": self.VERSION or 1,
            "active_version_id": self.ACTIVEVERSIONID,
        }

    class Meta:
        managed = False
        db_table = 'ECOLOGY"."WORKFLOW_BASE'
        verbose_name = verbose_name_plural = "OA流程信息"


class WorkflowNodeBase(OADbBaseModel):
    """
    流程节点基本信息
    """

    ID = models.IntegerField(primary_key=True)
    NODENAME = models.CharField(  # noqa: DJ001
        max_length=300, blank=True, null=True, verbose_name="节点名称"
    )
    ISSTART = models.CharField(
        verbose_name="是否创建节点", max_length=10
    )  # 0：否，1：是
    ISREJECT = models.CharField(
        verbose_name="当前节点是否可以退回", max_length=10
    )  # 0：否，1：是
    ISREOPEN = models.CharField(
        verbose_name="是否重新打开", max_length=10
    )  # 0：否，1：是
    ISEND = models.CharField(verbose_name="是否归档节点", max_length=10)  # 0：否，1：是

    class Meta:
        managed = False
        db_table = 'ECOLOGY"."WORKFLOW_NODEBASE'
        verbose_name = verbose_name_plural = "OA流程节点基础信息"


class WorkflowFlowNode(OADbBaseModel):
    """
    流程流转节点
    """

    # ID = models.IntegerField(db_column="NODEID", primary_key=True)
    WORKFLOWID = models.ForeignKey(
        WorkflowBase,
        db_column="WORKFLOWID",
        to_field="ID",
        on_delete=models.DO_NOTHING,
        related_name="nodes",
        verbose_name="所属流程",
    )
    NODEORDER = models.IntegerField(verbose_name="顺序")
    NODEID = models.OneToOneField(
        WorkflowNodeBase,
        on_delete=models.DO_NOTHING,
        db_column="NODEID",
        to_field="ID",
        primary_key=True,
        related_name="+",
        verbose_name="节点信息",
    )
    ISSELECTREJECTNODE = models.SmallIntegerField(
        null=True, choices=OAWFRejectType.choices, verbose_name="退回方式"
    )
    REJECTABLENODES = models.TextField(  # noqa: DJ001
        null=True, blank=True, verbose_name="指定可退回节点"
    )
    ISSUBMITDIRECTNODE = models.CharField(  # noqa: DJ001
        max_length=10,
        null=True,
        blank=True,
        choices=OAWFHandleReSubmit.choices,
        verbose_name="退回后再提交到达节点处理方式",
    )
    ISSUBMITDIRECTNODEDEFT = models.CharField(  # noqa: DJ001
        max_length=10,
        null=True,
        blank=True,
        choices=OAWFHandleReSubmitDefault.choices,
        verbose_name="默认退回后再提交到达节点处理方式",
    )
    NODETYPE = models.CharField(  # noqa: DJ001
        max_length=10,
        null=True,
        blank=True,
        choices=OAFlowNodeType.choices,
        verbose_name="节点类型",
    )

    class Meta:
        managed = False
        db_table = 'ECOLOGY"."WORKFLOW_FLOWNODE'
        verbose_name = verbose_name_plural = "OA流程下的节点"

    def into_srm_dict(self):
        return {
            "work_flow_id": self.WORKFLOWID_id,
            "node_order": self.NODEORDER,
            "node_id": self.NODEID_id,
            "node_name": self.NODEID.NODENAME,
            "is_start": self.NODEID.ISSTART,
            "is_reject": self.NODEID.ISREJECT,
            "is_reopen": self.NODEID.ISREOPEN,
            "is_end": self.NODEID.ISEND,
        }


class WorkflowNodeLink(OADbBaseModel):
    """
    流程节点出口信息
    """

    WORKFLOWID = models.ForeignKey(
        WorkflowBase,
        db_column="WORKFLOWID",
        to_field="ID",
        on_delete=models.DO_NOTHING,
        related_name="node_relations",
        verbose_name="所属流程",
    )
    NODEID = models.ForeignKey(
        WorkflowNodeBase,
        db_column="NODEID",
        to_field="ID",
        on_delete=models.DO_NOTHING,
        related_name="to_relations",
        verbose_name="节点信息",
    )
    DESTNODEID = models.ForeignKey(
        WorkflowNodeBase,
        db_column="DESTNODEID",
        to_field="ID",
        on_delete=models.DO_NOTHING,
        related_name="from_relations",
        verbose_name="目标节点",
    )
    ISREJECT = models.CharField(
        verbose_name="节点是否可退回", max_length=10
    )  # 0：否，1：是
    LINKNAME = models.CharField(verbose_name="出口名称", max_length=1000)

    class Meta:
        managed = False
        db_table = 'ECOLOGY"."WORKFLOW_NODELINK'
        verbose_name = verbose_name_plural = "OA流程节点出口"

    def into_srm_dict(self):
        return {
            "from_node_id": self.NODEID_id,
            "from_node_name": self.NODEID.NODENAME,
            "to_node_id": self.DESTNODEID_id,
            "to_node_name": self.DESTNODEID.NODENAME,
            "link_name": self.LINKNAME,
        }


class WorkflowRequestLog(OADbBaseModel):
    """
    流程请求签字日志
    """

    LOGID = models.IntegerField(primary_key=True)
    REQUESTID = models.ForeignKey(
        "WorkflowRequestBase",
        db_column="REQUESTID",
        to_field="REQUESTID",
        null=True,
        on_delete=models.DO_NOTHING,
        related_name="request_logs",
        verbose_name="所属流程请求",
    )
    NODEID = models.ForeignKey(
        WorkflowNodeBase,
        db_column="NODEID",
        to_field="ID",
        null=True,
        on_delete=models.DO_NOTHING,
        related_name="+",
        verbose_name="当前节点ID",
    )
    DESTNODEID = models.ForeignKey(
        WorkflowNodeBase,
        db_column="DESTNODEID",
        to_field="ID",
        null=True,
        on_delete=models.DO_NOTHING,
        related_name="+",
        verbose_name="所属节点",
    )
    LOGTYPE = models.CharField(  # noqa: DJ001
        max_length=100,
        choices=OAWorkflowLogTypes.choices,
        null=True,
        blank=True,
        verbose_name="操作类型",
    )
    OPERATOR = models.ForeignKey(
        "drf_oa_workflow.HRMResource",
        db_column="OPERATOR",
        to_field="ID",
        null=True,
        on_delete=models.DO_NOTHING,
        related_name="+",
        verbose_name="操作人ID",
    )
    OPERATEDATE = models.CharField(  # noqa: DJ001
        max_length=200, null=True, blank=True, verbose_name="操作日期"
    )
    OPERATETIME = models.CharField(  # noqa: DJ001
        max_length=200, null=True, blank=True, verbose_name="操作时间"
    )
    RECEIVEDPERSONS = models.TextField(null=True, blank=True, verbose_name="接收人")  # noqa: DJ001
    RECEIVEDPERSONIDS = models.TextField(  # noqa: DJ001
        null=True, blank=True, verbose_name="接收人IDS"
    )
    REMARK = models.TextField(null=True, blank=True, verbose_name="操作备注")  # noqa: DJ001

    class Meta:
        managed = False
        db_table = 'ECOLOGY"."WORKFLOW_REQUESTLOG'
        verbose_name = verbose_name_plural = "OA流程操作记录"


class WorkflowRequestBase(OADbBaseModel):
    """
    OA流程请求表
    """

    REQUESTID = models.IntegerField(primary_key=True)
    WORKFLOWID = models.ForeignKey(
        WorkflowBase,
        db_column="WORKFLOWID",
        to_field="ID",
        null=True,
        on_delete=models.DO_NOTHING,
        related_name="+",
        verbose_name="流程ID",
    )
    REQUESTMARK = models.CharField(  # noqa: DJ001
        max_length=200, null=True, blank=True, verbose_name="编号"
    )
    REQUESTNAME = models.CharField(  # noqa: DJ001
        max_length=200, null=True, blank=True, verbose_name="标题"
    )
    # CURRENTNODEID = models.IntegerField(verbose_name="当前节点ID")
    CURRENTNODEID = models.ForeignKey(
        WorkflowNodeBase,
        db_column="CURRENTNODEID",
        to_field="ID",
        null=True,
        on_delete=models.DO_NOTHING,
        related_name="+",
        verbose_name="当前节点ID",
    )
    STATUS = models.CharField(  # noqa: DJ001
        max_length=200, null=True, blank=True, verbose_name="状态"
    )
    CREATER = models.ForeignKey(
        "drf_oa_workflow.HRMResource",
        db_column="CREATER",
        to_field="ID",
        null=True,
        on_delete=models.DO_NOTHING,
        related_name="+",
        verbose_name="创建人ID",
    )
    LASTOPERATOR = models.ForeignKey(
        "drf_oa_workflow.HRMResource",
        db_column="LASTOPERATOR",
        to_field="ID",
        null=True,
        on_delete=models.DO_NOTHING,
        related_name="+",
        verbose_name="最后操作人ID",
    )
    CREATEDATE = models.CharField(  # noqa: DJ001
        max_length=200, null=True, blank=True, verbose_name="创建日期"
    )
    CREATETIME = models.CharField(  # noqa: DJ001
        max_length=200, null=True, blank=True, verbose_name="创建时间"
    )
    LASTOPERATEDATE = models.CharField(  # noqa: DJ001
        max_length=200, null=True, blank=True, verbose_name="最后操作日期"
    )
    LASTOPERATETIME = models.CharField(  # noqa: DJ001
        max_length=200, null=True, blank=True, verbose_name="最后操作时间"
    )
    REQUESTLEVEL = models.CharField(  # noqa: DJ001
        max_length=200, null=True, blank=True, verbose_name="紧急度"
    )

    objects = WorkflowManager()

    class Meta:
        managed = False
        db_table = 'ECOLOGY"."WORKFLOW_REQUESTBASE'
        verbose_name = verbose_name_plural = "OA流程信息"


class WorkflowRequestOperateLog(OADbBaseModel):
    ID = models.IntegerField(primary_key=True)
    REQUESTID = models.ForeignKey(
        WorkflowRequestBase,
        db_column="REQUESTID",
        to_field="REQUESTID",
        null=True,
        on_delete=models.DO_NOTHING,
        related_name="request_operate_logs",
        verbose_name="所属流程请求",
    )
    NODEID = models.ForeignKey(
        WorkflowNodeBase,
        db_column="NODEID",
        to_field="ID",
        on_delete=models.DO_NOTHING,
        related_name="+",
        verbose_name="节点信息",
    )
    ISREMARK = models.IntegerField(null=True, verbose_name="操作状态")
    OPERATORID = models.ForeignKey(
        "drf_oa_workflow.HRMResource",
        db_column="OPERATORID",
        to_field="ID",
        null=True,
        on_delete=models.DO_NOTHING,
        related_name="+",
        verbose_name="操作人ID",
    )
    OPERATEDATE = models.CharField(max_length=200, blank=True, verbose_name="操作日期")
    OPERATETIME = models.CharField(max_length=200, blank=True, verbose_name="操作时间")
    OPERATETYPE = models.CharField(
        max_length=200,
        blank=True,
        choices=OAWFOperateType.choices,
        verbose_name="操作类型",
    )
    OPERATENAME = models.CharField(
        max_length=200, blank=True, verbose_name="操作类型中文名称"
    )
    OPERATECODE = models.IntegerField(
        null=True, choices=OAWFOperateCode.choices, verbose_name="操作类型代码"
    )
    ISINVALID = models.CharField(
        max_length=20, blank=True, verbose_name="是否执行了强制收回"
    )
    INVALIDID = models.ForeignKey(
        "drf_oa_workflow.HRMResource",
        db_column="INVALIDID",
        to_field="ID",
        null=True,
        on_delete=models.DO_NOTHING,
        related_name="+",
        verbose_name="执行强制收回的用户id",
    )
    INVALIDDATE = models.CharField(
        max_length=200, blank=True, verbose_name="强制收回操作日期"
    )
    INVALIDTIME = models.CharField(
        max_length=200, blank=True, verbose_name="强制收回操作时间"
    )

    class Meta:
        managed = False
        db_table = 'ECOLOGY"."WORKFLOW_REQUESTOPERATELOG'
        verbose_name = verbose_name_plural = "OA流程操作记录日志主表"

    def __str__(self):
        return self.OPERATENAME
