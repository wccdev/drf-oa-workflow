from rest_framework.routers import DefaultRouter

from drf_oa_workflow.views.workflow_register import OAWorkflowConfViewSet
from drf_oa_workflow.views.workflow_register import OAWorkflowNodeViewSet

router = DefaultRouter()

# 流程注册信息
router.register("workflows", OAWorkflowConfViewSet)
router.register("workflows-nodes", OAWorkflowNodeViewSet)

urlpatterns = router.urls
