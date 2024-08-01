from rest_framework.routers import DefaultRouter

from drf_oa_workflow.views.workflow_approval import WorkflowApprovalViewSet
from drf_oa_workflow.views.workflow_approval import WorkflowsViewSet
from drf_oa_workflow.views.workflow_register import RegisterWorkflowNodeViewSet
from drf_oa_workflow.views.workflow_register import RegisterWorkflowViewSet

router = DefaultRouter()

# 流程注册信息
router.register("register-workflows", RegisterWorkflowViewSet)
router.register("register-workflows-nodes", RegisterWorkflowNodeViewSet)

# 流程待办/已办
router.register("workflows", WorkflowsViewSet)
# 流程审批等操作
router.register("approvals", WorkflowApprovalViewSet)

urlpatterns = router.urls
