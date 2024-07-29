from rest_framework.routers import DefaultRouter

from drf_oa_workflow.views.approval import WorkflowApprovalViewSet
from drf_oa_workflow.views.approval import WorkflowsViewSet
from drf_oa_workflow.views.workflow_register import OAWorkflowConfViewSet
from drf_oa_workflow.views.workflow_register import OAWorkflowNodeViewSet

router = DefaultRouter()

# 流程注册信息
router.register("workflow-classes", OAWorkflowConfViewSet)
router.register("workflow-classes-nodes", OAWorkflowNodeViewSet)

# 流程待办/已办
router.register("workflow-list", WorkflowsViewSet)
# 流程审批等操作
router.register("workflow-approvals", WorkflowApprovalViewSet)

urlpatterns = router.urls
