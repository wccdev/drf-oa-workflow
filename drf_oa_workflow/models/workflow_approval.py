from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

from drf_oa_workflow.choices import ApprovalStatus
from drf_oa_workflow.choices import OAWorkflowLogTypes
from drf_oa_workflow.choices import WFOperationTypes
from drf_oa_workflow.choices import WorkflowAction

from .base import BaseAuditModel
from .workflow_register import OAWorkflow


class WorkflowApproval(BaseAuditModel):
    """
    流程记录
    """

    code = models.CharField(
        verbose_name="流程编号", max_length=128, blank=True, default=""
    )
    title = models.CharField(
        verbose_name="流程标题", max_length=256, blank=True, default=""
    )
    workflow = models.ForeignKey(
        to=OAWorkflow, on_delete=models.DO_NOTHING, verbose_name="流程"
    )
    workflow_request_id = models.CharField(verbose_name="OA流程实例ID", max_length=128)
    # 业务数据
    content_type = models.ForeignKey(
        to=ContentType, on_delete=models.DO_NOTHING, verbose_name="业务类型", null=True
    )
    object_id = models.PositiveIntegerField(verbose_name="业务数据ID", null=True)
    content_object = GenericForeignKey(
        "content_type", "object_id", for_concrete_model=False
    )
    approval_status = models.SmallIntegerField(
        verbose_name="审批状态", choices=ApprovalStatus, default=ApprovalStatus.PENDING
    )
    action = models.SmallIntegerField(
        verbose_name="触发类型", choices=WorkflowAction, default=WorkflowAction.ADD
    )
    archived_at = models.DateTimeField("流程结束时间", null=True, blank=True)
    front_form_info = models.JSONField("流程表单信息(前端)", null=True, default=dict)

    LOG_TYPE = {i[0]: i[1] for i in OAWorkflowLogTypes.choices}

    # 以下3个属性含义参考 drf_oa_workflow.models.workflow_register.OAWorkflow
    TERMINATE_COLUMN = OAWorkflow.TERMINATE_COLUMN
    DEFAULT_MAIN_DATA = OAWorkflow.DEFAULT_MAIN_DATA
    TERMINATE_MAIN_DATA = OAWorkflow.TERMINATE_MAIN_DATA

    class Meta:
        verbose_name = verbose_name_plural = "流程审核"
        db_table = "workflow_approval"

    def __str__(self):
        return self.title

    def archive(self):
        """
        流程结束
        """
        # assert not self.archived_at, "流程已归档"
        archived_time = timezone.now()
        self.updated_at = archived_time
        self.archived_at = archived_time
        self.save()

    def get_oa_request_code(self):
        """
        获取oa流程编号
        """
        from .oa_workflow import WorkflowRequestBase

        oa_wf = WorkflowRequestBase.objects.filter(
            REQUESTID=self.workflow_request_id
        ).first()
        if oa_wf:
            self.code = oa_wf.REQUESTMARK
        else:
            self.code = ""
        return self.code

    def record_operation(  # noqa: PLR0913
        self, operator, oa_node_id, operation_type, oa_log_id=None, remark=""
    ) -> None:
        """
        记录流程操作
        :param operator:        操作人
        :param oa_node_id:      操作人当前节点
        :param operation_type:  操作类型
        :param oa_log_id:       操作记录ID
        :param remark:          签字意见、审批备注等
        """
        WorkflowApprovalOperation.objects.create(
            created_by=operator,
            updated_by=operator,
            approval=self,
            oa_node_id=oa_node_id,
            operation_type=operation_type,
            remark=remark,
            oa_log_id=oa_log_id,
        )


class WorkflowApprovalOperation(BaseAuditModel):
    approval = models.ForeignKey(
        to=WorkflowApproval,
        on_delete=models.DO_NOTHING,
        verbose_name="流程记录",
        related_name="operations",
    )
    oa_node_id = models.IntegerField("OA流程节点ID")
    operation_type = models.SmallIntegerField("操作类型", choices=WFOperationTypes)
    remark = models.TextField("意见", blank=True, default="")
    oa_log_id = models.IntegerField("OA流程审批记录ID", null=True)

    class Meta:
        verbose_name = verbose_name_plural = "流程操作记录"
        db_table = "workflow_approval_operation"

    def __str__(self):
        return self.get_operation_type_display()
