# import datetime
#
# from rest_framework.decorators import action
# from rest_framework.response import Response
from rest_framework.views import APIView

from .mixin import OaWFApiViewMixin


class OaWorkFlowView(OaWFApiViewMixin, APIView):
    # TODO 通用流程接口
    ...
