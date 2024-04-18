import datetime

from django.db import models

from drf_oa_workflow.choices import OAWFCOIsRemarks, OAWFCOViewType, OAWorkflowLogTypes
from drf_oa_workflow.db.manager import CurrentOperatorManager, WorkflowManager
from drf_oa_workflow.db.models import OADbBaseModel


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
    USERTYPE = models.IntegerField(null=True, verbose_name="用户类型(1、人力资源; 2、客户)")
    VIEWTYPE = models.IntegerField(null=True, choices=OAWFCOViewType.choices, verbose_name="查看标志")
    ISREMARK = models.IntegerField(null=True, choices=OAWFCOIsRemarks.choices, verbose_name="操作类型")
    ISLASTTIMES = models.IntegerField(null=True)
    ISREJECT = models.CharField(max_length=100, null=True, blank=True, verbose_name="是否为退回前的节点操作人")
    ISBEREJECT = models.CharField(max_length=100, null=True, blank=True, verbose_name="是否退回")
    RECEIVEDATE = models.CharField(max_length=200, null=True, blank=True, verbose_name="接收日期")
    RECEIVETIME = models.CharField(max_length=200, null=True, blank=True, verbose_name="接收时间")
    VIEWDATE = models.CharField(max_length=200, null=True, blank=True, verbose_name="查看日期")
    VIEWTIME = models.CharField(max_length=200, null=True, blank=True, verbose_name="查看时间")
    FIRSTVIEWDATE = models.CharField(max_length=200, null=True, blank=True, verbose_name="初次查看日期")
    FIRSTVIEWTIME = models.CharField(max_length=200, null=True, blank=True, verbose_name="初次查看时间")
    OPERATEDATE = models.CharField(max_length=200, null=True, blank=True, verbose_name="操作日期")
    OPERATETIME = models.CharField(max_length=200, null=True, blank=True, verbose_name="操作时间")
    NODEID = models.IntegerField(null=True)
    AGENTORBYAGENTID = models.IntegerField(null=True)
    AGENTTYPE = models.CharField(max_length=200, null=True, blank=True)

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

        now = datetime.datetime.now()
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


class WorkflowBase(OADbBaseModel):
    """
    流程基本信息
    """

    ID = models.IntegerField(primary_key=True)
    WORKFLOWNAME = models.CharField(max_length=300, blank=True, null=True, verbose_name="流程名称")
    FORMID = models.IntegerField(verbose_name="表单ID")
    WORKFLOWTYPE = models.IntegerField(verbose_name="所属路径ID")
    ISVALID = models.IntegerField(verbose_name="生效信息")  # 0：无效 1：有效 2:测试 3:历史版本
    VERSION = models.IntegerField(verbose_name="版本", null=True)
    ISTEMPLATE = models.CharField(verbose_name="是否为流程模板", max_length=10, null=True)  # 0：否 1：是
    TEMPLATEID = models.IntegerField(verbose_name="模板ID", null=True)
    ACTIVEVERSIONID = models.IntegerField(verbose_name="当前流程所属活动版本id", null=True)

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
            "work_flow_type_id": self.WORKFLOWTYPE,
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
    NODENAME = models.CharField(max_length=300, blank=True, null=True, verbose_name="节点名称")
    ISSTART = models.CharField(verbose_name="是否创建节点", max_length=10)  # 0：否，1：是
    ISREJECT = models.CharField(verbose_name="当前节点是否可以退回", max_length=10)  # 0：否，1：是
    ISREOPEN = models.CharField(verbose_name="是否重新打开", max_length=10)  # 0：否，1：是
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
    ISREJECT = models.CharField(verbose_name="节点是否可退回", max_length=10)  # 0：否，1：是
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
    LOGTYPE = models.CharField(
        max_length=100, choices=OAWorkflowLogTypes.choices, null=True, blank=True, verbose_name="操作类型"
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
    OPERATEDATE = models.CharField(max_length=200, null=True, blank=True, verbose_name="操作日期")
    OPERATETIME = models.CharField(max_length=200, null=True, blank=True, verbose_name="操作时间")
    RECEIVEDPERSONS = models.TextField(null=True, blank=True, verbose_name="接收人")
    RECEIVEDPERSONIDS = models.TextField(null=True, blank=True, verbose_name="接收人IDS")
    REMARK = models.TextField(null=True, blank=True, verbose_name="操作备注")

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
    REQUESTMARK = models.CharField(max_length=200, null=True, blank=True, verbose_name="编号")
    REQUESTNAME = models.CharField(max_length=200, null=True, blank=True, verbose_name="标题")
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
    STATUS = models.CharField(max_length=200, null=True, blank=True, verbose_name="状态")
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
    CREATEDATE = models.CharField(max_length=200, null=True, blank=True, verbose_name="创建日期")
    CREATETIME = models.CharField(max_length=200, null=True, blank=True, verbose_name="创建时间")
    LASTOPERATEDATE = models.CharField(max_length=200, null=True, blank=True, verbose_name="最后操作日期")
    LASTOPERATETIME = models.CharField(max_length=200, null=True, blank=True, verbose_name="最后操作时间")
    REQUESTLEVEL = models.CharField(max_length=200, null=True, blank=True, verbose_name="紧急度")

    objects = WorkflowManager()

    class Meta:
        managed = False
        db_table = 'ECOLOGY"."WORKFLOW_REQUESTBASE'
        verbose_name = verbose_name_plural = "OA流程信息"