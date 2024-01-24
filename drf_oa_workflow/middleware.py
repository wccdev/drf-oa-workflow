from .handler import handle_request


class OaWFRequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(handle_request(request))
        return response
