from django.db.models import IntegerChoices, TextChoices


class TransmitTypes(IntegerChoices):
    FORWARD = 1, "转发"
    CONSULTATION = 2, "意见征询"
    TRANSFER = 3, "转办"


class WFOperationTypes(IntegerChoices):
    SUBMIT_WITHOUT_WF = 0, "不走流程提交"
    SUBMIT = 1, "提交"
    APPROVAL = 2, "批准"
    SAVE = 3, "保存"
    FORWARD = 4, "转发"
    FORWARD_ROLLBACK = 5, "转发收回"
    TRANSFER = 6, "转办"
    MARKUP = 7, "批注"
    REJECT = 8, "退回"
    WITHDRAW = 9, "撤回"
    CONSULTATION = 10, "意见征询"
    RE_SUBMIT = 11, "重新提交"  # 流程被退回时
    DO_FORCE_RECOVER = 12, "强制收回"
    DO_DELETE = 13, "删除流程"

    TERMINATE = 50, "终止"


class OAWorkflowLogTypes(TextChoices):
    # FIXME 确认OA不同环境关于LOGTYPE字段值与定义是否相同
    APPROVAL = "0", "批准"
    SAVE = "1", "保存"
    SUBMIT = "2", "提交"
    REJECT = "3", "退回"
    REOPEN = "4", "重新打开"
    DELETE = "5", "删除"
    ACTIVE = "6", "激活"
    FORWARD = "7", "转发"
    MARKUP = "9", "批注"
    CONSULTATION = "a", "意见征询"
    REPLY = "b", "意见征询回复"
    CIRCULATION = "c", "传阅"
    FORCE_ARCHIVE = "e", "强制归档"
    TRANSFER = "h", "转办"
    INTERVENE = "i", "流程干预"
    TRANSFER_REPLY = "j", "转办反馈"
    WITHDRAW = "r", "撤回"
    SUPERVISING = "s", "督办"
    CC = "t", "抄送"
    END_CONSULTATION = "x", "结束征询"
    CONSULTATION_TRANSFER = "z", "征询转办"


class OAWFCOViewType(IntegerChoices):
    VIEWED = -2, "已查看过流程，不显示任何new标记"
    VIEWED_WITHOUT_NEWEST = -1, "查看过流程后又有新的未查看回复，显示黄色new标记"
    UN_VIEW = 0, "接收到流程且未查看过，显示红色new标记"


class OAWFCOIsRemarks(IntegerChoices):
    NOT_OPERATED = 0, "未操作"
    TRANS = 1, "转发"
    OPERATED = 2, "已操作"
    ARCHIVED = 4, "归档"
    TIMEOUT = 5, "超时"
    AUTO_REVIEW = 6, "自动审批(审批中)"
    CC_WITHOUT_SUB = 8, "抄送(不需提交)"
    CC_WITH_SUB = 9, "抄送(需提交)"
    CIRCULATION = 11, "传阅"


class OAWFRejectType(IntegerChoices):
    BY_LINK = 0, "按出口退回"
    FREE = 1, "自由退回"
    APPOINT = 2, "在自定范围内退回"


class OAWFHandleReSubmit(TextChoices):
    BY_STEP = "0", "逐级审批"
    BY_DIRECT = "1", "直达本节点"
    BY_CHOICE = "2", "操作者选择"


class OAWFHandleReSubmitDefault(TextChoices):
    BY_STEP = "0", "逐级审批"
    BY_DIRECT = "1", "直达本节点"


class OAFlowNodeType(TextChoices):
    CREATE = "0", "创建"
    REVIEW = "1", "审批"
    SUBMIT = "2", "提交"
    ARCHIVE = "3", "归档"
