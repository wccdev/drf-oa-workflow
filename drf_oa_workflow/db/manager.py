from django.db import models
from django.db.models import Case, F, Q, Value, When

from .function import ConvertOADbDatetime


class BaseOADbManager(models.Manager):
    def __init__(self):
        super().__init__()
        self._db = "oa"

    def using(self, *args, **kwargs):
        return super().using("oa")


class CurrentOperatorManager(BaseOADbManager):
    def wf_un_operators(self):
        """
        流程当前节点未操作人
        """
        from drf_oa_workflow.choices import OAWFCOIsRemarks

        return (
            self.get_queryset()
            .filter(
                Q(
                    ISREMARK__in=[OAWFCOIsRemarks.NOT_OPERATED, OAWFCOIsRemarks.ARCHIVED, OAWFCOIsRemarks.CC_WITH_SUB],
                    OPERATEDATE__isnull=True,
                    OPERATETIME__isnull=True,
                )
                | Q(ISREMARK=OAWFCOIsRemarks.NOT_OPERATED),
                ISLASTTIMES=1,
                NODEID=F("REQUESTID__CURRENTNODEID_id"),
            )
            .annotate(
                un_operator_id=F("USERID_id"), un_operator_name=F("USERID__LASTNAME"), request_id=F("REQUESTID_id")
            )
            .distinct()
        )


class WorkflowQuerySet(models.QuerySet):
    def build_fields(self):
        return self.annotate(
            RECEIVEDATE=F("current_operators__RECEIVEDATE"),
            RECEIVETIME=F("current_operators__RECEIVETIME"),
            C_VIEWTYPE=F("current_operators__VIEWTYPE"),
            C_ISREMARRK=F("current_operators__ISREMARK"),
            C_NODEID=F("current_operators__NODEID"),
            C_ISREJECT=F("current_operators__ISREJECT"),
            C_ISBEREJECT=F("current_operators__ISBEREJECT"),
            # createTime=Concat(F("CREATEDATE"), Value(" "), F("CREATETIME")),
            # receiveTime=Concat(F("current_operators__RECEIVEDATE"), Value(" "), F("current_operators__RECEIVETIME")),
            # lastOperateTime=Concat(F("LASTOPERATEDATE"), Value(" "), F("LASTOPERATETIME")),
            createTime=ConvertOADbDatetime("CREATEDATE", "CREATETIME"),
            receiveTime=Case(
                When(
                    Q(current_operators__RECEIVEDATE__isnull=False, current_operators__RECEIVETIME__isnull=False),
                    then=ConvertOADbDatetime("current_operators__RECEIVEDATE", "current_operators__RECEIVETIME"),
                ),
                default=Value(None),
            ),
            lastOperateTime=Case(
                When(
                    Q(LASTOPERATEDATE__isnull=False, LASTOPERATETIME__isnull=False),
                    then=ConvertOADbDatetime("LASTOPERATEDATE", "LASTOPERATETIME"),
                ),
                default=Value(None),
            ),
        )

    def todo(self, oa_user_id, workflow_ids):
        """
        待办查询
        0：未操作;
        1：转发;
        2：已操作;
        4：归档;
        5：超时;
        6:自动审批（审批中）
        8：抄送(不需提交);
        9：抄送(需提交);
        11:传阅;
        """
        queryset = self.filter(
            current_operators__USERTYPE=0,
            current_operators__ISREMARK__in=[0, 1, 5, 7, 8, 9],
            current_operators__ISLASTTIMES=1,
            current_operators__USERID=oa_user_id,
            WORKFLOWID__in=workflow_ids,
        )
        return queryset.build_fields()

    def handled(self, oa_user_id, workflow_ids):
        queryset = self.filter(
            current_operators__USERTYPE=0,
            current_operators__ISREMARK__in=[2, 4],
            current_operators__ISLASTTIMES=1,
            current_operators__USERID=oa_user_id,
            WORKFLOWID__in=workflow_ids,
        )
        return queryset.build_fields()


class WorkflowManager(BaseOADbManager):
    def get_queryset(self):
        queryset = WorkflowQuerySet(self.model, using=self._db, hints=self._hints)
        return queryset
