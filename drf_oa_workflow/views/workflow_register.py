from drfexts.viewsets import ExtGenericViewSet
from rest_framework.mixins import ListModelMixin
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.mixins import UpdateModelMixin

from drf_oa_workflow.models import RegisterWorkflow
from drf_oa_workflow.models import RegisterWorkflowNode
from drf_oa_workflow.serializers import RegisterWorkflowNodeSerializer
from drf_oa_workflow.serializers import RegisterWorkflowRetrieveSerializer
from drf_oa_workflow.serializers import RegisterWorkflowSaveSerializer
from drf_oa_workflow.serializers import RegisterWorkflowSerializer

__all__ = [
    "RegisterWorkflowViewSet",
    "RegisterWorkflowNodeViewSet",
]


class RegisterWorkflowViewSet(
    ListModelMixin,
    UpdateModelMixin,
    RetrieveModelMixin,
    ExtGenericViewSet,
):
    queryset = RegisterWorkflow.objects.for_ordering().select_related("workflow_type")
    serializer_class = {
        "default": RegisterWorkflowSerializer,
        "create": RegisterWorkflowSaveSerializer,
        "update": RegisterWorkflowSaveSerializer,
        "partial_update": RegisterWorkflowSaveSerializer,
        "retrieve": RegisterWorkflowRetrieveSerializer,
    }
    ordering = ("workflow_type_id", "order")


class RegisterWorkflowNodeViewSet(
    ListModelMixin,
    UpdateModelMixin,
    RetrieveModelMixin,
    ExtGenericViewSet,
):
    queryset = RegisterWorkflowNode.objects.all()
    serializer_class = RegisterWorkflowNodeSerializer
    filterset_fields = ["workflow_id"]
