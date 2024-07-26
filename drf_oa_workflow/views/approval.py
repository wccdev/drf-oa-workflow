from django.db.models import Q
from rest_framework.exceptions import APIException
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from drf_oa_workflow.mixin import OaWFApiViewMixin
from drf_oa_workflow.models import OAWorkflow
from drf_oa_workflow.models import WorkflowRequestBase
from drf_oa_workflow.serializers.approval import TodoHandledListSerializer


def filter_workflow(qs, name, value):
    ids = list(
        OAWorkflow.objects.filter(
            Q(id=int(value)) | Q(parent__id=int(value))
        ).values_list("workflow_id", flat=True)
    )
    return qs.filter(WORKFLOWID_id__in=ids)


class WorkflowsViewSet(OaWFApiViewMixin, ListModelMixin, GenericViewSet):
    queryset = WorkflowRequestBase.objects.all()
    serializer_class = TodoHandledListSerializer
    ordering = ("-lastOperateTime",)

    # filterset_fields = {
    #     "workflowBaseInfo.workflowId": django_filters.NumberFilter(method=filter_workflow),  # noqa: E501
    # }
    search_fields = ["REQUESTMARK", "REQUESTNAME", "WORKFLOWID__WORKFLOWNAME"]

    @classmethod
    def get_essential_factor(cls, request):
        try:
            oa_user_id = request.user.oa_user_id
        except APIException:
            oa_user_id = None
        workflow_ids = list(OAWorkflow.objects.values_list("workflow_id", flat=True))

        return oa_user_id, workflow_ids

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("CREATER", "LASTOPERATOR", "CURRENTNODEID", "WORKFLOWID")
        )

    def _list(self, queryset):
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    # @extend_schema(
    #     parameters=[
    #         OpenApiParameter(
    #             name="list_target",
    #             location=OpenApiParameter.QUERY,
    #             required=True,
    #             description="请求流程类型[todo: 待办; handled: 已办]",
    #             enum=["todo", "handled"],
    #             type=OpenApiTypes.STR,
    #             default="todo",
    #             allow_blank=False,
    #         )
    #     ]
    # )
    def list(self, request, *args, **kwargs):
        oa_user_id, workflow_ids = self.get_essential_factor(request)
        if not oa_user_id or not workflow_ids:
            return Response()

        list_target = request.GET.get("list_target", "todo") or "todo"
        if list_target == "todo":
            self.ordering = ("-receiveTime",)
            queryset = self.get_queryset().todo(oa_user_id, workflow_ids)
        else:
            queryset = self.get_queryset().handled(oa_user_id, workflow_ids)
        return self._list(self.filter_queryset(queryset))
