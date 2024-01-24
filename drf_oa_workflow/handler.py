from django.utils.functional import SimpleLazyObject

from .utils import OaWorkFlow


def get_handler(request):
    if not hasattr(request, "_oa_wf_api"):
        request._oa_wf_api = OaWorkFlow()
    try:
        oa_user_id = request.user.oa_user_id
    except AttributeError:
        raise AttributeError("request.user对象需提供'oa_user_id'属性, 该值为当前登入用户对应oa的user_id")
    request._oa_wf_api.register_user(oa_user_id)
    return request._oa_wf_api


def handle_request(request):
    request.oa_wf_api = SimpleLazyObject(lambda: get_handler(request))
    return request
