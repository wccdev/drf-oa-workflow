from .handler import handle_request


class OaWFApiViewMixin:
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(handle_request(request), *args, **kwargs)
