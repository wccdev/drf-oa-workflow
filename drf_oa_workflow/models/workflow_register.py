from __future__ import annotations

from django.db import models
from django.db.models import F
from django.db.models import Q

from drf_oa_workflow import choices
from drf_oa_workflow.apps import OaWorkflowApiConfig
from drf_oa_workflow.models import WorkflowBase
from drf_oa_workflow.models import WorkflowFlowNode
from drf_oa_workflow.models import WorkflowNodeLink
from drf_oa_workflow.models.base import BaseModel
from drf_oa_workflow.settings import SETTING_PREFIX
from drf_oa_workflow.settings import api_settings
from drf_oa_workflow.utils import OaWorkflowApi

__all__ = [
    "RegisterWorkflowType",
    "RegisterWorkflow",
    "RegisterWorkflowNode",
    "RegisterWorkflowEdge",
]


class WorkflowQuerySet(models.QuerySet):
    def for_ordering(self):
        return self.annotate(
            wf_id=models.Case(
                models.When(parent_id__isnull=True, then=models.F("workflow_id")),
                default=models.F("parent_id"),
            )
        )


class WorkflowManager(models.Manager):
    def get_queryset(self):
        return WorkflowQuerySet(self.model, using=self._db, hints=self._hints)

    def for_ordering(self):
        return self.get_queryset().for_ordering()

    def get_by_code(self, code) -> RegisterWorkflow:
        """
        通过流程code获取流程类
        """
        obj: RegisterWorkflow = (
            self.get_queryset().select_related("active_version").get(code=code)
        )
        if not obj.active_version_id or obj.active_version_id == obj.workflow_id:
            return obj
        return obj.active_version


class RegisterWorkflowType(BaseModel):
    workflow_type_id = models.IntegerField("OA流程目录ID", unique=True)
    workflow_type_name = models.CharField("OA流程目录", max_length=500)
    desc = models.CharField("描述", max_length=500, blank=True, default="")
    order = models.IntegerField("顺序", null=True, blank=True)
    uuid = models.CharField("UUID", max_length=100, blank=True, default="")

    def __str__(self):
        return self.workflow_type_name

    class Meta:
        verbose_name = verbose_name_plural = "流程目录注册"
        db_table = f"{OaWorkflowApiConfig.name}_register_workflow_type"


class RegisterWorkflow(BaseModel):
    """
    OA流程注册
    """

    code = models.CharField("流程编号", max_length=128, blank=True, default="")
    name = models.CharField("流程名称", max_length=128)
    workflow_id = models.IntegerField("OA流程ID", unique=True)
    workflow_type = models.ForeignKey(
        to=RegisterWorkflowType,
        on_delete=models.DO_NOTHING,
        to_field="workflow_type_id",
        verbose_name="OA流程所属目录",
    )
    workflow_form_id = models.IntegerField("OA流程表单ID", null=True)
    workflow_main_table = models.CharField("OA流程主表", max_length=128)
    workflow_detail_tables = models.JSONField("OA流程子表", blank=True, default=list)
    is_active_version = models.SmallIntegerField(
        "使用版本", choices=choices.OAWorkflowActiveChoices, null=True
    )
    workflow_version = models.IntegerField("OA流程版本", null=True)
    file_category_id = models.IntegerField("OA流程附件目录ID", null=True)
    parent = models.ForeignKey(
        to="self",
        on_delete=models.PROTECT,
        to_field="workflow_id",
        null=True,
        verbose_name="父级",
    )
    active_version = models.ForeignKey(
        to="self",
        on_delete=models.DO_NOTHING,
        to_field="workflow_id",
        null=True,
        related_name="other_versions",
        verbose_name="所属活动流程",
    )
    order = models.IntegerField("OA流程顺序", null=True)
    remark = models.TextField("备注", max_length=500, blank=True, default="")

    form_permissions = models.JSONField(
        verbose_name="节点表单权限", null=True, blank=True, default=dict
    )

    objects = WorkflowManager()

    def __str__(self):
        return f"{self.workflow_id}-{self.name}-版本{self.workflow_version}"

    @classmethod
    def sync_other_versions(cls, register_workflow_id: int | None = None) -> None:
        """
        同步流程在OA中的其他版本
        """

        if register_workflow_id:
            register_workflow_ids = [register_workflow_id]
        else:
            register_workflow_ids = list(
                cls.objects.filter(workflow_version=1).values_list(
                    "workflow_id", flat=True
                )
            )

        oa_wfs = (
            WorkflowBase.objects.annotate(
                workflow_type_name=F("WORKFLOWTYPE__TYPENAME")
            )
            .filter(
                Q(ID__in=register_workflow_ids)
                | Q(TEMPLATEID__in=register_workflow_ids)
            )
            .exclude(ISTEMPLATE="1")
        )

        workflows = []
        for i in oa_wfs:
            w = {
                "workflow_id": i.ID,
                "name": i.WORKFLOWNAME,
                "workflow_type_id": i.WORKFLOWTYPE_id,
                "workflow_form_id": i.FORMID,
                "is_active_version": i.ISVALID,
                "parent_id": i.TEMPLATEID if i.VERSION else None,
                "workflow_version": i.VERSION or 1,
                "active_version_id": i.ACTIVEVERSIONID,
                "order": i.DSPORDER,
            }
            workflow_main_table = f"formtable_main_{0 - int(w['workflow_form_id'])}"
            workflows.append(cls(**w, workflow_main_table=workflow_main_table))
        cls.objects.bulk_create(
            workflows,
            update_conflicts=True,
            unique_fields=["workflow_id"],
            update_fields=[
                "name",
                "workflow_id",
                "workflow_type_id",
                "workflow_form_id",
                "is_active_version",
                "workflow_version",
                "workflow_main_table",
                "parent_id",
                "active_version_id",
                "order",
            ],
        )

    def sync_nodes_from_oa(self):
        """
        同步流程在OA中的节点信息
        """

        oa_nodes = (
            WorkflowFlowNode.objects.select_related("NODEID")
            .filter(WORKFLOWID_id=self.workflow_id)
            .order_by("NODEORDER")
        )
        flow_nodes = [
            RegisterWorkflowNode(
                workflow_id=i.WORKFLOWID_id,
                node_order=i.NODEORDER,
                node_id=i.NODEID_id,
                node_name=i.NODEID.NODENAME,
                is_start=i.NODEID.ISSTART,
                is_reject=i.NODEID.ISREJECT,
                is_reopen=i.NODEID.ISREOPEN,
                is_end=i.NODEID.ISEND,
                register_workflow=self,
                status=choices.StatusChoice.VALID,
            )
            for i in oa_nodes
        ]

        RegisterWorkflowNode.objects.bulk_create(
            flow_nodes,
            update_conflicts=True,
            update_fields=[
                "status",
                "register_workflow",
                "workflow_id",
                "node_order",
                "node_name",
                "is_start",
                "is_reject",
                "is_reopen",
                "is_end",
            ],
            unique_fields=["node_id"],
        )
        RegisterWorkflowNode.objects.exclude(
            node_id__in=[i.node_id for i in flow_nodes]
        ).filter(register_workflow_id=self.pk).update(
            status=choices.StatusChoice.INVALID
        )

    def sync_node_relations_from_oa(self):
        """
        同步流程在OA中的节点关系
        """

        oa_node_links = WorkflowNodeLink.objects.select_related(
            "NODEID", "DESTNODEID"
        ).filter(WORKFLOWID_id=self.workflow_id)
        flow_node_relations = [
            RegisterWorkflowEdge(
                from_node_id=i.NODEID_id,
                from_node_name=i.NODEID.NODENAME,
                to_node_id=i.DESTNODEID_id,
                to_node_name=i.DESTNODEID.NODENAME,
                link_name=i.LINKNAME,
                register_workflow=self,
            )
            for i in oa_node_links
        ]

        RegisterWorkflowEdge.objects.filter(register_workflow=self).delete()
        RegisterWorkflowEdge.objects.bulk_create(flow_node_relations)

    def get_chart_url(self, manager_uid):
        """
        获取流程配置的流程图链接
        """
        # 需要OA高权限账号
        return OaWorkflowApi().get_workflow_chart_url(manager_uid, self.workflow_id)

    @property
    def chart_url(self):
        if not api_settings.OA_WORKFLOW_MANAGER_LOGINID:
            raise ValueError(
                "若要查看流程图，"
                "请先在django settings中设置具有OA流程管理权限的账号LOGINID:"
                f"\n{SETTING_PREFIX} = {'{'}"
                '\n    "OA_WORKFLOW_MANAGER_LOGINID": "xxxxx",'
                "\n    ..."
                "\n}"
            )
        return self.get_chart_url(api_settings.OA_WORKFLOW_MANAGER_LOGINID)

    class Meta:
        verbose_name = verbose_name_plural = "流程注册"
        db_table = f"{OaWorkflowApiConfig.name}_register_workflow"


class RegisterWorkflowNode(BaseModel):
    """
    流程下的节点
    """

    ONE_ZERO_CHOICES = (
        ("1", "是"),
        ("0", "否"),
    )

    register_workflow = models.ForeignKey(
        to=RegisterWorkflow,
        on_delete=models.CASCADE,
        null=True,
        related_name="flow_nodes",
        verbose_name="所属流程",
    )
    workflow_id = models.IntegerField(verbose_name="OA流程ID")
    node_order = models.IntegerField(verbose_name="OA流程节点顺序")
    node_id = models.IntegerField(verbose_name="OA流程节点ID", unique=True)
    node_name = models.CharField(
        verbose_name="OA流程节点名", max_length=256, blank=True, default=""
    )
    is_start = models.CharField(
        verbose_name="开始节点",
        max_length=10,
        blank=True,
        default="",
        choices=ONE_ZERO_CHOICES,
    )
    is_reject = models.CharField(
        verbose_name="IS REJECT",
        max_length=10,
        blank=True,
        default="",
        choices=ONE_ZERO_CHOICES,
    )
    is_reopen = models.CharField(
        verbose_name="IS REOPEN",
        max_length=10,
        blank=True,
        default="",
        choices=ONE_ZERO_CHOICES,
    )
    is_end = models.CharField(
        verbose_name="结束节点",
        max_length=10,
        blank=True,
        default="",
        choices=ONE_ZERO_CHOICES,
    )
    form_permissions = models.JSONField(
        verbose_name="节点表单权限", null=True, blank=True, default=dict
    )

    def __str__(self):
        return f"{self.workflow_id}-{self.node_name}"

    class Meta:
        verbose_name = verbose_name_plural = "流程节点"
        db_table = f"{OaWorkflowApiConfig.name}_register_workflow_node"


class RegisterWorkflowEdge(BaseModel):
    register_workflow = models.ForeignKey(
        to=RegisterWorkflow,
        on_delete=models.CASCADE,
        null=True,
        related_name="flow_node_relations",
        verbose_name="所属流程",
    )
    from_node = models.ForeignKey(
        to=RegisterWorkflowNode,
        on_delete=models.DO_NOTHING,
        to_field="node_id",
        null=True,
        related_name="output_edges",
        verbose_name="FROM节点ID",
    )
    from_node_name = models.CharField(
        verbose_name="FROM节点名", max_length=256, blank=True, default=""
    )
    to_node = models.ForeignKey(
        to=RegisterWorkflowNode,
        on_delete=models.DO_NOTHING,
        to_field="node_id",
        null=True,
        related_name="input_edges",
        verbose_name="TO节点ID",
    )
    to_node_name = models.CharField(
        verbose_name="TO节点名", max_length=256, blank=True, default=""
    )
    link_name = models.CharField(
        verbose_name="流程出口名称", max_length=500, blank=True, default=""
    )

    def __str__(self):
        return f"{self.from_node_name}->{self.to_node_name}"

    class Meta:
        verbose_name = verbose_name_plural = "流程节点关系"
        db_table = f"{OaWorkflowApiConfig.name}_register_workflow_edge"
