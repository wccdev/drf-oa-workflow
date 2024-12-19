from django.db.models import IntegerChoices
from django.db.models import TextChoices


class SubmitTypes(TextChoices):
    # 提交（创建）流程时的提交类型
    SAVE = "0", "保存"  # 流程在创建节点暂存，不会转到第2个节点
    SUBMIT = "1", "提交"  # 流程自动流转到第2个节点


class SubmitFailedDoes(TextChoices):
    NOT_DELETE = "0", "不删除"
    DELETE = "1", "删除"


class ReviewTypes(TextChoices):
    # 审批（创建）流程时的提交类型
    SAVE = "save", "保存"  # 不会流转到下个节点
    SUBMIT = "submit", "提交"  # 会流转到下个节点


class StatusChoice(IntegerChoices):
    INVALID = 0, "无效"
    VALID = 1, "有效"


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


# 目前收集到的所有OA WORKFLOW_REQUESTOPERATELOG 表中的操作类型
OA_WORKFLOW_OPERATES = [
    {"number": -2, "code": "forward", "name": "转发"},
    {"number": 0, "code": "supervise", "name": "监督"},
    {"number": 0, "code": "chuanyue", "name": "传阅"},
    {"number": 1, "code": "submit", "name": "提交"},
    {"number": 2, "code": "reject", "name": "退回"},
    {"number": 3, "code": "intervenor", "name": "干预"},
    {"number": 4, "code": "trans", "name": "转办"},
    {"number": 5, "code": "take", "name": "意见征询"},
    {"number": 6, "code": "takForward", "name": "征询转办"},
    {"number": 7, "code": "takEnd", "name": "结束征询"},
    {"number": 9, "code": "forceover", "name": "强制归档"},
    {"number": 10, "code": "forwardreply", "name": "转发批注"},
    {"number": 11, "code": "takereply", "name": "意见征询回复"},
    {"number": 12, "code": "withdraw", "name": "撤回"},
]


class OAWFOperateType(TextChoices):
    """ """

    FORWARD = "forward", "转发"
    CIRCULATE = "chuanyue", "传阅"
    SUBMIT = "submit", "提交"
    REJECT = "reject", "退回"
    INTERVENDOR = "intervenor", "干预"
    TRANS = "trans", "转办"
    TAKE = "take", "意见征询"
    TAKE_FORWARD = "takForward", "征询转办"
    TAKE_END = "takEnd", "结束征询"
    FORCE_OVER = "forceover", "强制归档"
    FORWARD_REPLY = "forwardreply", "转发批注"
    TAKE_REPLY = "takereply", "意见征询回复"
    WITHDRAW = "withdraw", "撤回"


class OAWFOperateCode(IntegerChoices):
    """ """

    FORWARD = -2, "转发"
    CIRCULATE = 0, "传阅"
    SUBMIT = 1, "提交"
    REJECT = 2, "退回"
    INTERVENDOR = 3, "干预"
    TRANS = 4, "转办"
    TAKE = 5, "意见征询"
    TAKE_FORWARD = 6, "征询转办"
    TAKE_END = 7, "结束征询"
    FORCE_OVER = 9, "强制归档"
    FORWARD_REPLY = 10, "转发批注"
    TAKE_REPLY = 11, "意见征询回复"
    WITHDRAW = 12, "撤回"
