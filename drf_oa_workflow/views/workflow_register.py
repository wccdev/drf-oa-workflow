from rest_framework.mixins import ListModelMixin
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.mixins import UpdateModelMixin

from drf_oa_workflow.models import OAWorkflow
from drf_oa_workflow.models import OAWorkflowNode
from drf_oa_workflow.serializers import OAWorkflowConfRetrieveSerializer
from drf_oa_workflow.serializers import OAWorkflowConfSaveSerializer
from drf_oa_workflow.serializers import OAWorkflowConfSerializer
from drf_oa_workflow.serializers import OAWorkflowNodeRetrieveSerializer
from drf_oa_workflow.serializers import OAWorkflowNodeSerializer

from .base import CusGenericViewSet

__all__ = [
    "OAWorkflowConfViewSet",
    "OAWorkflowNodeViewSet",
]


class OAWorkflowConfViewSet(
    ListModelMixin,
    UpdateModelMixin,
    RetrieveModelMixin,
    CusGenericViewSet,
):
    queryset = OAWorkflow.objects.for_ordering().select_related("workflow_type")
    serializer_class = {
        "default": OAWorkflowConfSerializer,
        "create": OAWorkflowConfSaveSerializer,
        "update": OAWorkflowConfSaveSerializer,
        "partial_update": OAWorkflowConfSaveSerializer,
        "retrieve": OAWorkflowConfRetrieveSerializer,
    }
    ordering = ("workflow_type_id", "order")


class OAWorkflowNodeViewSet(
    ListModelMixin,
    UpdateModelMixin,
    RetrieveModelMixin,
    CusGenericViewSet,
):
    queryset = OAWorkflowNode.objects.all()
    serializer_class = {
        "default": OAWorkflowNodeSerializer,
        "retrieve": OAWorkflowNodeRetrieveSerializer,
    }
    filterset_fields = ["workflow_id"]