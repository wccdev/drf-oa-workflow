from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone
from rest_framework.exceptions import APIException

from drf_oa_workflow.choices import ApprovalStatus
from drf_oa_workflow.choices import DocStatus
from drf_oa_workflow.choices import StatusChoice
from drf_oa_workflow.choices import WorkflowAction


class BaseModel(models.Model):
    """
    标准抽象模型,可直接继承使用
    """

    status = models.SmallIntegerField(
        verbose_name="状态", choices=StatusChoice.choices, default=StatusChoice.VALID
    )
    deleted_at = models.DateTimeField("删除时间", editable=False, null=True, blank=True)
    created_at = models.DateTimeField(verbose_name="新增时间", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="更新时间", auto_now=True)

    objects = models.Manager()

    class Meta:
        abstract = True
        verbose_name = "基础模型"


class BaseAuditModel(BaseModel):
    """
    标准抽象审计模型,可直接继承使用
    """

    created_by = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.DO_NOTHING,
        related_name="+",
        verbose_name="创建人",
    )
    updated_by = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.DO_NOTHING,
        related_name="+",
        verbose_name="修改人",
    )

    class Meta:
        abstract = True
        verbose_name = "基础审计模型"


class BaseApprovalModel(BaseAuditModel):
    """
    标准抽象审批模型,可直接继承使用
    """

    status = models.SmallIntegerField(
        verbose_name="状态",
        choices=DocStatus,
        default=DocStatus.DRAT,
        db_default=DocStatus.DRAT,
    )
    valid_from = models.DateTimeField(verbose_name="生效时间", null=True, blank=True)
    approval_status = models.SmallIntegerField(
        verbose_name="审批状态", choices=ApprovalStatus, null=True
    )
    workflow_approval = models.ForeignKey(
        to="drf_oa_workflow.Approval",
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        verbose_name="流程审批",
    )

    class Meta:
        abstract = True
        verbose_name = "基础审批模型"

    @classmethod
    def get_workflow_class(cls, action):
        """
        提供自身绑定的系统流程配置的编号，获取需要使用的流程的编号
        :param action:
        :type action:  WorkflowAction
        :return:
        :rtype:
        """
        raise NotImplementedError

    def submit(  # noqa: PLR0913
        self,
        action=WorkflowAction.ADD,
        title: str = "",
        remark: str = "",
        submitter=None,
        front_form_info=None,
        main_data: dict | None = None,
        detail_data: list | None = None,
    ):
        """
        提交
        :param action:      提交的流程Action类型,用于确定提交流程的code
        :param title:       提交的流程标题
        :param remark:      提交意见或者审批意见
        :param submitter:   流程提交人, 没有的话取当前数据updated_by
        :param front_form_info:  前端表单信息
        :param main_data:   提交到OA的数据，无特殊逻辑一般情况都不需要
            - {"oa主表单字段名": "字段值"}
        :param detail_data: 子表数据，无特殊逻辑一般情况都不需要
        """
        from drf_oa_workflow.service import WFService

        # assert front_form_info and isinstance(front_form_info, (dict, list)),
        # "需要定义好的前端流程表单信息"

        if self.workflow_approval_id:
            raise APIException("该数据流程已提交，请勿重复提交！")

        # 1.action类型 确定数据提交流程后的状态
        if action in [WorkflowAction.ADD, WorkflowAction.EDIT, WorkflowAction.VALID]:
            self.status = DocStatus.TO_VALID
        else:
            self.status = DocStatus.TO_INVALID
        self.approval_status = ApprovalStatus.PENDING

        # 2.获取提交的流程类
        wf_class = self.get_workflow_class(action=action)

        # 3.提交到OA
        self.workflow_approval = WFService.submit_oa(
            self,
            wf_class,
            action,
            title,
            front_form_info,
            main_data=main_data,
            detail_data=detail_data,
            remark=remark,
            submitter=submitter,
        )

        self.save()

    def rollback(self):
        """
        流程审核拒绝后回调，业务数据回滚
        """
        # TODO 业务model重写rollback方法,提供数据回滚功能
        raise NotImplementedError

    def invalid(self):
        """
        失效
        """
        self.status = DocStatus.TO_INVALID
        self.approval_status = ApprovalStatus.PENDING
        self.save()

    def approve(self):
        """
        审批通过(默认行为)
          --业务单据根据自己的逻辑重写或者覆盖此方法
        """
        if self.status == DocStatus.TO_VALID:
            self.status = DocStatus.VALID
            self.valid_from = timezone.now()
        elif self.status == DocStatus.TO_INVALID:
            self.status = DocStatus.INVALID
            self.valid_from = None
        self.approval_status = ApprovalStatus.APPROVED
        self.save()

    def reject(self, reason=None):
        """
        审批拒绝(默认行为)
          --业务单据根据自己的逻辑重写或者覆盖此方法
        """
        self.status = DocStatus.DRAT
        self.approval_status = ApprovalStatus.REJECTED
        # 历史版本回滚
        self.save()

    def cancel(self):
        """
        取消流程（流程被删除）(默认行为)
          --业务单据根据自己的逻辑重写或者覆盖此方法
        流程发起人在流程被退回到发起节点时可以删除该流程，
        业务根据需求自己写逻辑
        """
        # FIXME 暂且 置空workflow_approval  置空approval_status  重置status为待提交
        # FIXME 以下确认，覆盖此方法需要 super().cancel()
        self.workflow_approval = None
        self.approval_status = None
        # TODO 单据状态
        # self.status = CommonStatus.DRAT
        self.save()
